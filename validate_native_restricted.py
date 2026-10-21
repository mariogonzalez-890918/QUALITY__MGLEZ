"""Regresión elevada aislada: reproduce ERROR_ACCESS_DENIED de Server, sin datos reales."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

import ntsecuritycon as rights
import win32api
import win32con
import win32security as security


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--previous-helper')
    args = parser.parse_args()
    if not ctypes.windll.shell32.IsUserAnAdmin():
        raise RuntimeError('Esta prueba aislada requiere elevación.')
    project = Path(__file__).resolve().parent
    helper = project / 'build/native/QualityLiteSetupHelper.exe'
    sandbox = Path(tempfile.mkdtemp(prefix='QualityLite-acl-regression-'))
    data = sandbox / 'Datos á'
    logs = data / 'logs'
    logs.mkdir(parents=True)
    log_file = logs / 'qualitylite.log'
    log_file.write_text('Registro ficticio que debe conservarse.\n', encoding='utf-8')
    digest = hashlib.sha256(log_file.read_bytes()).hexdigest()
    system = security.ConvertStringSidToSid('S-1-5-18')
    everyone = security.ConvertStringSidToSid('S-1-1-0')
    token = security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_ADJUST_PRIVILEGES | win32con.TOKEN_QUERY)
    previous = security.AdjustTokenPrivileges(token, False, [
        (security.LookupPrivilegeValue(None, 'SeRestorePrivilege'), security.SE_PRIVILEGE_ENABLED)])
    try:
        # El propietario SYSTEM impide la concesión implícita de READ_CONTROL al usuario.
        restricted = security.ACL()
        restricted.AddAccessDeniedAce(security.ACL_REVISION, rights.FILE_ALL_ACCESS, everyone)
        restricted.AddAccessAllowedAce(security.ACL_REVISION, rights.FILE_ALL_ACCESS, system)
        for target in (log_file,):
            security.SetNamedSecurityInfo(str(target), security.SE_FILE_OBJECT,
                security.OWNER_SECURITY_INFORMATION | security.DACL_SECURITY_INFORMATION | security.PROTECTED_DACL_SECURITY_INFORMATION,
                system, None, restricted, None)
    finally:
        security.AdjustTokenPrivileges(token, False, previous)
        token.Close()
    ordinary_denied = False
    try:
        security.GetNamedSecurityInfo(str(log_file), security.SE_FILE_OBJECT, security.DACL_SECURITY_INFORMATION)
    except Exception as error:
        ordinary_denied = getattr(error, 'winerror', None) == 5
    assert ordinary_denied, 'La prueba no reprodujo la denegación de lectura de ACL.'
    old_code = None
    if args.previous_helper:
        old_code = subprocess.run([args.previous_helper, '--root', str(data), '--log', str(sandbox/'previous.log')]).returncode
        assert old_code == 5, f'El preparador anterior debía fallar con código 5, recibió {old_code}'
    result = subprocess.run([str(helper), '--root', str(data), '--log', str(sandbox/'fixed.log')])
    assert result.returncode == 0, (sandbox/'fixed.log').read_text(encoding='utf-8')
    # Segundo escenario: además del archivo, el directorio no permite enumeración.
    token = security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_ADJUST_PRIVILEGES | win32con.TOKEN_QUERY)
    previous = security.AdjustTokenPrivileges(token, False, [
        (security.LookupPrivilegeValue(None, 'SeRestorePrivilege'), security.SE_PRIVILEGE_ENABLED)])
    try:
        for target in (log_file, logs):
            security.SetNamedSecurityInfo(str(target), security.SE_FILE_OBJECT,
                security.OWNER_SECURITY_INFORMATION | security.DACL_SECURITY_INFORMATION | security.PROTECTED_DACL_SECURITY_INFORMATION,
                system, None, restricted, None)
    finally:
        security.AdjustTokenPrivileges(token, False, previous)
        token.Close()
    folder_result = subprocess.run([str(helper), '--root', str(data), '--log', str(sandbox/'fixed-directory.log')])
    assert folder_result.returncode == 0, (sandbox/'fixed-directory.log').read_text(encoding='utf-8')
    assert hashlib.sha256(log_file.read_bytes()).hexdigest() == digest
    expected = {'S-1-5-18', 'S-1-5-19', 'S-1-5-32-544'}
    for target in (data, logs, log_file):
        descriptor = security.GetNamedSecurityInfo(str(target), security.SE_FILE_OBJECT,
            security.DACL_SECURITY_INFORMATION | security.OWNER_SECURITY_INFORMATION)
        acl = descriptor.GetSecurityDescriptorDacl()
        assert {security.ConvertSidToStringSid(acl.GetAce(i)[2]) for i in range(acl.GetAceCount())} == expected
        assert descriptor.GetSecurityDescriptorControl()[0] & security.SE_DACL_PROTECTED
        if target != data:
            assert security.ConvertSidToStringSid(descriptor.GetSecurityDescriptorOwner()) == 'S-1-5-18'
    assert subprocess.run([str(helper), '--root', str(data), '--log', str(sandbox/'fixed.log')]).returncode == 0
    # Un enlace en la carpeta de datos debe abortar antes de modificar cualquier ACL.
    before = security.GetNamedSecurityInfo(str(data), security.SE_FILE_OBJECT, security.DACL_SECURITY_INFORMATION)
    external = sandbox/'fuera'; external.mkdir()
    (external/'original.txt').write_text('No tocar', encoding='utf-8')
    os.symlink(external, data/'enlace', target_is_directory=True)
    rejected = subprocess.run([str(helper), '--root', str(data), '--log', str(sandbox/'reparse.log')]).returncode
    assert rejected != 0
    after = security.GetNamedSecurityInfo(str(data), security.SE_FILE_OBJECT, security.DACL_SECURITY_INFORMATION)
    assert bytes(before) == bytes(after)
    assert (external/'original.txt').read_text(encoding='utf-8') == 'No tocar'
    report = {'version': '0.2.1', 'result': 'passed', 'windows': subprocess.check_output(
        ['powershell.exe', '-NoProfile', '-Command', '(Get-CimInstance Win32_OperatingSystem).Caption'], text=True).strip(),
        'ordinary_acl_read_error': 5, 'previous_helper_exit': old_code, 'fixed_helper_exit': result.returncode,
        'exact_log_file_denial_reproduced': True, 'restricted_directory_exit': folder_result.returncode,
        'restricted_file_and_directory_recovered': True, 'owner_preserved': True,
        'file_hash_preserved': True, 'acl_principals_verified': True, 'idempotent': True,
        'reparse_rejected_without_acl_changes': True, 'tested_on_actual_windows_server': False}
    (project/'release/prueba-acl-restringida-0.2.1.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
