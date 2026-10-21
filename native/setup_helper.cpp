// Bootstrap nativo: Win32 y CRT estatica; no depende de Python, .NET ni VC Redist.
#define UNICODE
#define _UNICODE
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <sddl.h>
#include <string>
#include <vector>
#include <stdexcept>
#include <algorithm>

struct Failure { DWORD code; std::wstring message; };
static HANDLE logHandle=INVALID_HANDLE_VALUE;
static void Log(const std::wstring& message) {
 std::wstring line=message+L"\r\n";
 int size=WideCharToMultiByte(CP_UTF8,0,line.data(),(int)line.size(),nullptr,0,nullptr,nullptr);
 std::string bytes(size,' '); WideCharToMultiByte(CP_UTF8,0,line.data(),(int)line.size(),bytes.data(),size,nullptr,nullptr);
 DWORD written=0;
 if(logHandle!=INVALID_HANDLE_VALUE) { WriteFile(logHandle,bytes.data(),size,&written,nullptr); FlushFileBuffers(logHandle); }
}
static void Fail(DWORD code,const std::wstring& action,const std::wstring& path=L"") {
 wchar_t* description=nullptr;
 FormatMessageW(FORMAT_MESSAGE_ALLOCATE_BUFFER|FORMAT_MESSAGE_FROM_SYSTEM|FORMAT_MESSAGE_IGNORE_INSERTS,nullptr,code,0,(LPWSTR)&description,0,nullptr);
 std::wstring message=action+L" [Windows "+std::to_wstring(code)+L"] "+(description?description:L"")+L" "+path;
 if(description)LocalFree(description);
 throw Failure{code,message};
}
struct Target { std::wstring path; bool directory; std::vector<BYTE> original; bool wasProtected; };
static void Collect(const std::wstring& path,std::vector<Target>& targets) {
 DWORD attributes=GetFileAttributesW(path.c_str());
 if(attributes==INVALID_FILE_ATTRIBUTES)Fail(GetLastError(),L"No se pudieron leer atributos",path);
 if(attributes&FILE_ATTRIBUTE_REPARSE_POINT)Fail(ERROR_REPARSE_TAG_INVALID,L"Ruta con enlace, junction o reparse point no admitido; no se modificaron permisos",path);
 Target target{path,(attributes&FILE_ATTRIBUTE_DIRECTORY)!=0,{},false};
 DWORD needed=0;
 GetFileSecurityW(path.c_str(),DACL_SECURITY_INFORMATION,nullptr,0,&needed);
 if(!needed)Fail(GetLastError(),L"No se pueden respaldar permisos; revise propietario o politica del dominio",path);
 target.original.resize(needed);
 if(!GetFileSecurityW(path.c_str(),DACL_SECURITY_INFORMATION,(PSECURITY_DESCRIPTOR)target.original.data(),needed,&needed))Fail(GetLastError(),L"No se pudieron leer permisos",path);
 SECURITY_DESCRIPTOR_CONTROL control; DWORD revision;
 if(!GetSecurityDescriptorControl((PSECURITY_DESCRIPTOR)target.original.data(),&control,&revision))Fail(GetLastError(),L"Descriptor de seguridad invalido",path);
 target.wasProtected=(control&SE_DACL_PROTECTED)!=0;
 targets.push_back(std::move(target));
 if(!(attributes&FILE_ATTRIBUTE_DIRECTORY))return;
 WIN32_FIND_DATAW data;
 HANDLE search=FindFirstFileW((path+L"\\*").c_str(),&data);
 if(search==INVALID_HANDLE_VALUE) { if(GetLastError()==ERROR_FILE_NOT_FOUND)return; Fail(GetLastError(),L"No se pudo enumerar la carpeta",path); }
 try {
  do {
   if(wcscmp(data.cFileName,L".")&&wcscmp(data.cFileName,L".."))Collect(path+L"\\"+data.cFileName,targets);
  }while(FindNextFileW(search,&data));
  DWORD error=GetLastError(); if(error!=ERROR_NO_MORE_FILES)Fail(error,L"Enumeracion incompleta",path);
 }catch(...){ FindClose(search); throw; }
 FindClose(search);
}
static DWORD Secure(const std::wstring& input) {
 wchar_t root[32768];
 DWORD length=GetFullPathNameW(input.c_str(),32768,root,nullptr);
 if(!length||length>=32768)Fail(ERROR_INVALID_NAME,L"Directorio de datos invalido",input);
 std::wstring path(root); while(path.size()>3&&path.back()==L'\\')path.pop_back();
 if(path.size()<=3||path.rfind(L"\\\\",0)==0)Fail(ERROR_INVALID_NAME,L"Use una carpeta local; no una raiz ni una ruta UNC",path);
 SID_IDENTIFIER_AUTHORITY authority=SECURITY_NT_AUTHORITY; PSID admins=nullptr;
 if(!AllocateAndInitializeSid(&authority,2,SECURITY_BUILTIN_DOMAIN_RID,DOMAIN_ALIAS_RID_ADMINS,0,0,0,0,0,0,&admins))Fail(GetLastError(),L"No se pudo comprobar elevacion");
 BOOL admin=FALSE; BOOL checked=CheckTokenMembership(nullptr,admins,&admin); FreeSid(admins);
 if(!checked||!admin)Fail(ERROR_ELEVATION_REQUIRED,L"Ejecute el instalador con una cuenta administradora elevada");
 if(!CreateDirectoryW(path.c_str(),nullptr)&&GetLastError()!=ERROR_ALREADY_EXISTS)Fail(GetLastError(),L"No se pudo crear el directorio de datos",path);
 wchar_t volume[MAX_PATH]; DWORD flags=0;
 if(!GetVolumePathNameW(path.c_str(),volume,MAX_PATH)||!GetVolumeInformationW(volume,nullptr,0,nullptr,nullptr,&flags,nullptr,0))Fail(GetLastError(),L"No se pudo comprobar el volumen de datos",path);
 if(!(flags&FILE_PERSISTENT_ACLS))Fail(ERROR_NOT_SUPPORTED,L"El volumen debe admitir permisos persistentes NTFS/ReFS",path);
 std::vector<Target> targets; Collect(path,targets);
 // Convertir la SDDL completa evita diferencias de idioma o resolucion de cuentas.
 PSECURITY_DESCRIPTOR directories=nullptr,files=nullptr;
 if(!ConvertStringSecurityDescriptorToSecurityDescriptorW(L"D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;0x1301bf;;;LS)",SDDL_REVISION_1,&directories,nullptr))Fail(GetLastError(),L"No se pudo crear ACL de directorios");
 if(!ConvertStringSecurityDescriptorToSecurityDescriptorW(L"D:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;0x1301bf;;;LS)",SDDL_REVISION_1,&files,nullptr)) { LocalFree(directories); Fail(GetLastError(),L"No se pudo crear ACL de archivos"); }
 std::vector<size_t> changed;
 try {
  for(size_t i=targets.size();i-->0;) {
   const auto& target=targets[i];
   if(!SetFileSecurityW(target.path.c_str(),DACL_SECURITY_INFORMATION|PROTECTED_DACL_SECURITY_INFORMATION,target.directory?directories:files))Fail(GetLastError(),L"No se pudieron aplicar permisos; revise propietario, antivirus o GPO",target.path);
   changed.push_back(i);
  }
 }catch(...) {
  // Revertir exclusivamente las ACL tocadas; nunca borrar ni alterar datos.
  for(auto index=changed.rbegin();index!=changed.rend();++index) {
   const auto& target=targets[*index];
   DWORD flags=DACL_SECURITY_INFORMATION|(target.wasProtected?PROTECTED_DACL_SECURITY_INFORMATION:UNPROTECTED_DACL_SECURITY_INFORMATION);
   if(!SetFileSecurityW(target.path.c_str(),flags,(PSECURITY_DESCRIPTOR)target.original.data()))Log(L"ATENCION: no se pudo revertir ACL: "+target.path);
  }
  LocalFree(directories);LocalFree(files);throw;
 }
 LocalFree(directories);LocalFree(files);
 Log(L"OK: ACL aplicadas a "+std::to_wstring(targets.size())+L" objetos. Datos conservados.");
 return ERROR_SUCCESS;
}
static DWORD StopServiceControlled() {
 SC_HANDLE manager=OpenSCManagerW(nullptr,nullptr,SC_MANAGER_CONNECT);
 if(!manager)Fail(GetLastError(),L"No se pudo consultar el administrador de servicios");
 SC_HANDLE service=OpenServiceW(manager,L"QualityLite",SERVICE_QUERY_STATUS|SERVICE_STOP);
 if(!service) {
  DWORD code=GetLastError();CloseServiceHandle(manager);
  if(code==ERROR_SERVICE_DOES_NOT_EXIST){Log(L"OK: no hay un servicio previo.");return 0;}
  Fail(code,L"No se pudo abrir el servicio QualityLite");
 }
 try {
  SERVICE_STATUS status{};
  if(!QueryServiceStatus(service,&status))Fail(GetLastError(),L"No se pudo consultar el servicio");
  if(status.dwCurrentState!=SERVICE_STOPPED&&status.dwCurrentState!=SERVICE_STOP_PENDING)
   if(!ControlService(service,SERVICE_CONTROL_STOP,&status)&&GetLastError()!=ERROR_SERVICE_NOT_ACTIVE)Fail(GetLastError(),L"No se pudo detener QualityLite");
  ULONGLONG deadline=GetTickCount64()+30000;
  do {
   if(!QueryServiceStatus(service,&status))Fail(GetLastError(),L"No se pudo comprobar la parada");
   if(status.dwCurrentState==SERVICE_STOPPED)break;
   if(GetTickCount64()>deadline)Fail(ERROR_TIMEOUT,L"El servicio no se detuvo en 30 segundos; no se reemplazaron archivos");
   Sleep(250);
  }while(true);
 }catch(...){CloseServiceHandle(service);CloseServiceHandle(manager);throw;}
 CloseServiceHandle(service);CloseServiceHandle(manager);Log(L"OK: servicio detenido.");return 0;
}
int wmain(int argc,wchar_t** argv) {
 if(argc==2&&wcscmp(argv[1],L"--version")==0)return 0;
 std::wstring root,log;bool stop=false;
 for(int i=1;i<argc;i++) {
  if(wcscmp(argv[i],L"--root")==0&&i+1<argc)root=argv[++i];
  else if(wcscmp(argv[i],L"--log")==0&&i+1<argc)log=argv[++i];
  else if(wcscmp(argv[i],L"--stop-service")==0)stop=true;
 }
 if(!log.empty())logHandle=CreateFileW(log.c_str(),FILE_APPEND_DATA,FILE_SHARE_READ|FILE_SHARE_WRITE,nullptr,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
 DWORD result=0;
 try {
  Log(L"QualityLite SetupHelper 0.1.2 - bootstrap nativo Win32 x64 /MT");
  if((root.empty()&&!stop)||logHandle==INVALID_HANDLE_VALUE)Fail(ERROR_INVALID_PARAMETER,L"Se requieren --root y --log con rutas escribibles");
  result=stop?StopServiceControlled():Secure(root);
 }catch(const Failure& failure) { Log(L"ERROR: "+failure.message); result=failure.code; }
 catch(...) { Log(L"ERROR: fallo interno del preparador nativo."); result=ERROR_GEN_FAILURE; }
 if(logHandle!=INVALID_HANDLE_VALUE)CloseHandle(logHandle);
 return (int)result;
}
