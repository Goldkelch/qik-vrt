// QIKVRT V2.13.4AW Commercial Readiness Pack uploader
// Windows Script Host JScript. No PowerShell. No .ps1. No Git in installer.
// Masked token input uses a local HTA password dialog. Tokens are not printed or stored.
var fso = new ActiveXObject("Scripting.FileSystemObject");
var shell = new ActiveXObject("WScript.Shell");
var VERSION = "QIKVRT_V2_13_4AW_COMMERCIAL_READINESS_PACK";
var SEED_DEFAULT = "Goldkelch/qik-vrt";
var NODE_DEFAULT = "ingolf-lohmann/qik-vrt";
var BRANCH_DEFAULT = "main";
var API = "https://api.github.com";
function out(s){WScript.StdOut.WriteLine(s);} function write(s){WScript.StdOut.Write(s);} function trim(s){return String(s).replace(/^\s+|\s+$/g,"");}
function upper(s){return String(s).toUpperCase();} function accept(s){s=upper(trim(s)); return s==="JA"||s==="J"||s==="YES"||s==="Y";}
function promptLine(label, def){ if(def!==null&&def!==undefined&&def!=="") write(label+" ["+def+"]: "); else write(label+": "); var s=WScript.StdIn.ReadLine(); s=trim(s); if(s===""&&def!==null&&def!==undefined) return def; return s; }
function nowUtc(){var d=new Date(); function p(n){return n<10?"0"+n:""+n;} return d.getUTCFullYear()+p(d.getUTCMonth()+1)+p(d.getUTCDate())+"T"+p(d.getUTCHours())+p(d.getUTCMinutes())+p(d.getUTCSeconds())+"Z";}
function rand6(){return String(Math.floor(Math.random()*900000)+100000);} function sleep(ms){WScript.Sleep(ms);}
function jsStringLiteral(s){var r=String(s); r=r.replace(/\\/g,"\\\\"); r=r.replace(/'/g,"\\'"); r=r.replace(/\r/g,"\\r"); r=r.replace(/\n/g,"\\n"); return r;}
function htmlEscape(s){var r=String(s); r=r.replace(/&/g,"&amp;"); r=r.replace(/</g,"&lt;"); r=r.replace(/>/g,"&gt;"); r=r.replace(/\"/g,"&quot;"); return r;}
function jsonEscape(s){var r=String(s); r=r.replace(/\\/g,"\\\\").replace(/\"/g,"\\\"").replace(/\r/g,"\\r").replace(/\n/g,"\\n").replace(/\t/g,"\\t"); return r;}
function apiPathEncode(path){var parts=String(path).split("/"); for(var i=0;i<parts.length;i++) parts[i]=encodeURIComponent(parts[i]); return parts.join("/");}
function which(cmd){try{var e=shell.Exec("cmd /c where "+cmd+" 2>nul"); while(e.Status===0) sleep(50); return e.ExitCode===0;}catch(ex){return false;}}
function maskedTokenPrompt(title){
  var envName = title.indexOf("SEED")>=0 ? "QIKVRT_SEED_TOKEN" : "QIKVRT_NODE_TOKEN";
  try { var ev=shell.ExpandEnvironmentStrings("%"+envName+"%"); if(ev!=="%"+envName+"%" && trim(ev)!==""){ out("MASKED_TOKEN_SOURCE "+envName+" environment variable present"); return trim(ev); } } catch(e0){}
  if(!which("mshta.exe")){ throw new Error("TOKEN_MASKING_UNAVAILABLE mshta.exe not found or disabled; set "+envName+" and rerun"); }
  var tmp=shell.ExpandEnvironmentStrings("%TEMP%"); var stamp=nowUtc()+"_"+rand6();
  var hta=fso.BuildPath(tmp,"qikvrt_4aw_token_prompt_"+stamp+".hta"); var outFile=fso.BuildPath(tmp,"qikvrt_4aw_token_value_"+stamp+".txt");
  var html="<!DOCTYPE html>\r\n<html>\r\n<head>\r\n<title>QIKVRT Token Prompt</title>\r\n"+
    "<HTA:APPLICATION ID=\"qikvrt\" APPLICATIONNAME=\"QIKVRT\" BORDER=\"thin\" CAPTION=\"yes\" SHOWINTASKBAR=\"yes\" SINGLEINSTANCE=\"yes\" WINDOWSTATE=\"normal\">\r\n"+
    "<script language=\"javascript\" type=\"text/javascript\">\r\n"+
    "var qikvrtOutFile='"+jsStringLiteral(outFile)+"';\r\n"+
    "function qikvrtWriteToken(){\r\n"+
    "  var v=document.getElementById('qikvrt_token').value;\r\n"+
    "  var fso=new ActiveXObject('Scripting.FileSystemObject');\r\n"+
    "  var f=fso.CreateTextFile(qikvrtOutFile,true);\r\n"+
    "  f.Write(v); f.Close(); window.close();\r\n"+
    "}\r\n"+
    "function qikvrtCancel(){ window.close(); }\r\n"+
    "function window.onload(){ window.resizeTo(700,220); document.getElementById('qikvrt_token').focus(); }\r\n"+
    "function document.onkeydown(){ if (event.keyCode==13) qikvrtWriteToken(); if (event.keyCode==27) qikvrtCancel(); }\r\n"+
    "</script>\r\n</head>\r\n"+
    "<body style=\"font-family:Segoe UI,Arial,sans-serif;font-size:12pt\">\r\n"+
    "<p><b>"+htmlEscape(title)+"</b></p>\r\n"+
    "<p>Token is masked and used only for this local upload session.</p>\r\n"+
    "<input id=\"qikvrt_token\" type=\"password\" style=\"width:640px\" autocomplete=\"off\"/>\r\n"+
    "<p><input type=\"button\" value=\"OK\" onclick=\"qikvrtWriteToken()\"/> <input type=\"button\" value=\"Cancel\" onclick=\"qikvrtCancel()\"/></p>\r\n"+
    "</body>\r\n</html>\r\n";
  var f=fso.CreateTextFile(hta,true); f.Write(html); f.Close();
  out("MASKED_TOKEN_PROMPT opened for "+title); shell.Run("mshta.exe \""+hta+"\"",1,true);
  var token=""; if(fso.FileExists(outFile)){ var tf=fso.OpenTextFile(outFile,1,false); token=tf.ReadAll(); tf.Close(); }
  try{if(fso.FileExists(hta)) fso.DeleteFile(hta,true);}catch(e1){} try{if(fso.FileExists(outFile)) fso.DeleteFile(outFile,true);}catch(e2){}
  token=trim(token); if(token==="") throw new Error("MASKED_TOKEN_EMPTY_OR_CANCELLED "+title); out("MASKED_TOKEN_RECEIVED "+title); return token;
}
function http(method,url,token,body){ var req=null; try{req=new ActiveXObject("MSXML2.ServerXMLHTTP.6.0");}catch(e1){try{req=new ActiveXObject("MSXML2.ServerXMLHTTP");}catch(e2){req=new ActiveXObject("MSXML2.XMLHTTP");}}
  req.open(method,url,false); req.setRequestHeader("User-Agent","QIKVRT-4AW-Uploader"); req.setRequestHeader("Accept","application/vnd.github+json"); req.setRequestHeader("X-GitHub-Api-Version","2022-11-28"); if(token&&token!=="") req.setRequestHeader("Authorization","Bearer "+token); if(body!==null&&body!==undefined) req.setRequestHeader("Content-Type","application/json; charset=utf-8");
  try{req.send(body===null||body===undefined?null:body);}catch(ex){return {status:0,text:String(ex)};} return {status:req.status,text:req.responseText};}
function fileBase64(path){var stream=new ActiveXObject("ADODB.Stream"); stream.Type=1; stream.Open(); stream.LoadFromFile(path); var bytes=stream.Read(); stream.Close(); var dom=new ActiveXObject("MSXML2.DOMDocument.6.0"); var elem=dom.createElement("b64"); elem.dataType="bin.base64"; elem.nodeTypedValue=bytes; return String(elem.text).replace(/[\r\n]/g,"");}
function listFilesRecursive(root){var arr=[]; function walk(folder){var f=fso.GetFolder(folder); var files=new Enumerator(f.Files); for(;!files.atEnd();files.moveNext()) arr.push(String(files.item().Path)); var subs=new Enumerator(f.SubFolders); for(;!subs.atEnd();subs.moveNext()) walk(String(subs.item().Path));} walk(root); return arr;}
function relPath(root,path){var r=String(root), p=String(path); if(p.toLowerCase().indexOf(r.toLowerCase())===0) p=p.substring(r.length); while(p.charAt(0)==="\\"||p.charAt(0)==="/") p=p.substring(1); return p.replace(/\\/g,"/");}
function getExistingSha(repo,branch,targetPath,token){var url=API+"/repos/"+repo+"/contents/"+apiPathEncode(targetPath)+"?ref="+encodeURIComponent(branch); var res=http("GET",url,token,null); if(res.status===404) return ""; if(res.status!==200) throw new Error("GET_EXISTING_FAILED repo="+repo+" path="+targetPath+" http="+res.status+" body="+res.text.substring(0,600)); var m=/\"sha\"\s*:\s*\"([^\"]+)\"/.exec(res.text); return m?m[1]:"";}
function uploadFile(repo,branch,targetPath,sourcePath,token,msg){var b64=fileBase64(sourcePath); var sha=getExistingSha(repo,branch,targetPath,token); var body="{\"message\":\""+jsonEscape(msg)+"\",\"branch\":\""+jsonEscape(branch)+"\",\"content\":\""+b64+"\""; if(sha!=="") body+=",\"sha\":\""+jsonEscape(sha)+"\""; body+="}"; var res=http("PUT",API+"/repos/"+repo+"/contents/"+apiPathEncode(targetPath),token,body); if(res.status!==200&&res.status!==201) throw new Error("UPLOAD_FAILED repo="+repo+" path="+targetPath+" http="+res.status+" body="+res.text.substring(0,800)); out("PASS upload "+repo+" "+targetPath);}
function uploadRole(role,repo,branch,token){var root=fso.BuildPath(fso.GetAbsolutePathName("."),"roles\\"+role); if(!fso.FolderExists(root)) throw new Error("MISSING_ROLE_FOLDER "+root); var files=listFilesRecursive(root); out("QIKVRT_UPLOAD role="+role+" repo="+repo+" branch="+branch+" files="+files.length); for(var i=0;i<files.length;i++){var rp=relPath(root,files[i]); uploadFile(repo,branch,rp,files[i],token,"QIKVRT V2.13.4AW commercial readiness upload "+role+" "+rp);}}
try{
  out("QIKVRT V2.13.4AW Commercial Readiness Pack Uploader");
  out("No visible token prompt. Uploads commercial readiness documents to Seed and Node.");
  var acc=promptLine("Accept copyright and license? Type JA or YES","");
  if(!accept(acc)) throw new Error("COPYRIGHT_AND_LICENSE_NOT_ACCEPTED");
  var auth=promptLine("Confirm Product Owner commercial publication authorization? Type JA or YES","");
  if(!accept(auth)) throw new Error("PRODUCT_OWNER_PUBLICATION_NOT_AUTHORIZED");
  var seedRepo=promptLine("Seed repository",SEED_DEFAULT);
  var nodeRepo=promptLine("Node repository",NODE_DEFAULT);
  var seedBranch=promptLine("Seed branch",BRANCH_DEFAULT);
  var nodeBranch=promptLine("Node branch",BRANCH_DEFAULT);
  out("Seed target: "+seedRepo+" @ "+seedBranch);
  out("Node target: "+nodeRepo+" @ "+nodeBranch);
  var mode=upper(promptLine("Mode: DRYRUN or UPLOAD","DRYRUN"));
  if(mode!=="DRYRUN"&&mode!=="UPLOAD") throw new Error("INVALID_MODE");
  if(mode==="DRYRUN"){
    out("DRYRUN seed files="+listFilesRecursive(fso.BuildPath(fso.GetAbsolutePathName("."),"roles\\seed")).length);
    out("DRYRUN node files="+listFilesRecursive(fso.BuildPath(fso.GetAbsolutePathName("."),"roles\\node")).length);
    out("QIKVRT_4AW_COMMERCIAL_READINESS_FINAL PASS mode=DRYRUN");
    WScript.Quit(0);
  }
  out("UPLOAD mode selected. Tokens are requested in masked local dialogs.");
  out("SEED token scope needed for "+seedRepo+": Contents read/write.");
  var seedToken=maskedTokenPrompt("SEED TOKEN for repository "+seedRepo);
  var same=upper(promptLine("Use the same token also for NODE repository "+nodeRepo+"? Type YES only if this token has write access to that repo","NO"));
  var nodeToken="";
  if(same==="YES"||same==="JA"||same==="Y"||same==="J"){
    nodeToken=seedToken;
    out("TOKEN_REUSE_CONFIRMED for NODE repository "+nodeRepo);
  } else {
    out("NODE token scope needed for "+nodeRepo+": Contents read/write.");
    nodeToken=maskedTokenPrompt("NODE TOKEN for repository "+nodeRepo);
  }
  var fin=upper(promptLine("FINAL COMMERCIAL READINESS UPLOAD CONFIRMATION for BOTH repos. Type UPLOAD", ""));
  if(fin!=="UPLOAD") throw new Error("FINAL_UPLOAD_CONFIRMATION_NOT_GIVEN");
  uploadRole("seed", seedRepo, seedBranch, seedToken);
  uploadRole("node", nodeRepo, nodeBranch, nodeToken);
  out("QIKVRT_4AW_COMMERCIAL_READINESS_FINAL PASS mode=UPLOAD");
  WScript.Quit(0);
}catch(ex){
  out("BLOCK " + ex.message);
  WScript.Quit(90);
}

