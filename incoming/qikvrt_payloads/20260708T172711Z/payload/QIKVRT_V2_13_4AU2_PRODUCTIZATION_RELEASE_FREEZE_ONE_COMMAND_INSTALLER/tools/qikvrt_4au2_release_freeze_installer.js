// QIKVRT V2.13.4AU2 Productization Release Freeze Installer
// Windows Script Host JScript. No PowerShell. No .ps1. No Git command usage in installer.
// Token input is masked via local HTA password dialogs. Tokens are not printed, logged, or embedded.
// Creates release-freeze evidence files and GitHub Releases for Seed and Node.

var fso = new ActiveXObject("Scripting.FileSystemObject");
var shell = new ActiveXObject("WScript.Shell");
var GUID = "a84f157a-cef2-4c47-bca9-8f407085bdbe";
var SEED_DEFAULT = "Goldkelch/qik-vrt";
var NODE_DEFAULT = "ingolf-lohmann/qik-vrt";
var BRANCH_DEFAULT = "main";
var SEED_TAG_DEFAULT = "v2.13.4au1-seed-productization";
var NODE_TAG_DEFAULT = "v2.13.4au1-node-productization";
var PUBLIC_RUN_DEFAULT = "4AU_20260708T170628Z_362577";
var VERSION = "QIKVRT_V2_13_4AU2";

function out(s) { WScript.StdOut.WriteLine(s); }
function write(s) { WScript.StdOut.Write(s); }
function trim(s) { return String(s).replace(/^\s+|\s+$/g, ""); }
function upper(s) { return String(s).toUpperCase(); }
function ynAccept(s) { s = upper(trim(s)); return s === "JA" || s === "J" || s === "YES" || s === "Y"; }
function jsonEscape(s) { return String(s).replace(/\\/g,"\\\\").replace(/"/g,"\\\"").replace(/\r/g,"\\r").replace(/\n/g,"\\n").replace(/\t/g,"\\t"); }
function apiPathEncode(path) { var parts = String(path).split("/"); for (var i=0;i<parts.length;i++) parts[i] = encodeURIComponent(parts[i]); return parts.join("/"); }
function sleep(ms) { WScript.Sleep(ms); }
function pad(n) { return n < 10 ? "0" + n : "" + n; }
function nowRunId() { var d = new Date(); return "4AU2_" + d.getUTCFullYear() + pad(d.getUTCMonth()+1) + pad(d.getUTCDate()) + "T" + pad(d.getUTCHours()) + pad(d.getUTCMinutes()) + pad(d.getUTCSeconds()) + "Z_" + Math.floor(Math.random()*1000000); }
function isoUtc() { var d = new Date(); return d.getUTCFullYear()+"-"+pad(d.getUTCMonth()+1)+"-"+pad(d.getUTCDate())+"T"+pad(d.getUTCHours())+":"+pad(d.getUTCMinutes())+":"+pad(d.getUTCSeconds())+"Z"; }

function promptLine(label, def) {
  if (def !== null && def !== undefined && def !== "") write(label + " [" + def + "]: ");
  else write(label + ": ");
  var s = WScript.StdIn.ReadLine();
  s = trim(s);
  if (s === "" && def !== null && def !== undefined) return def;
  return s;
}

function which(cmd) {
  try {
    var e = shell.Exec("cmd /c where " + cmd + " 2>nul");
    while (e.Status === 0) sleep(50);
    return e.ExitCode === 0;
  } catch (ex) { return false; }
}

function tempName(prefix, ext) {
  var t = shell.ExpandEnvironmentStrings("%TEMP%");
  var n = prefix + "_" + String(new Date().getTime()) + "_" + String(Math.floor(Math.random()*1000000)) + ext;
  return fso.BuildPath(t, n);
}

function htaEscapeForJsString(s) {
  return String(s).replace(/\\/g,"\\\\").replace(/'/g,"\\'").replace(/\r/g," ").replace(/\n/g," ");
}

function readSecretHidden(label) {
  var envName = label.indexOf("SEED") >= 0 ? "QIKVRT_SEED_TOKEN" : "QIKVRT_NODE_TOKEN";
  try {
    var envVal = shell.ExpandEnvironmentStrings("%" + envName + "%");
    if (envVal !== "%" + envName + "%" && trim(envVal) !== "") {
      out("MASKED_TOKEN_SOURCE " + envName + " environment variable present");
      return trim(envVal);
    }
  } catch (ex0) {}
  if (!which("mshta.exe")) {
    out("BLOCK TOKEN_MASKING_UNAVAILABLE: mshta.exe not found or disabled. Token will not be requested visibly.");
    out("Set " + envName + " in a secure local environment and rerun, or enable mshta for the local password dialog.");
    WScript.Quit(31);
  }
  var outPath = tempName("qikvrt_token", ".txt");
  var htaPath = tempName("qikvrt_token_prompt", ".hta");
  var html = "<html><head><title>QIKVRT masked token input</title>" +
    "<HTA:APPLICATION ID='qikvrt' APPLICATIONNAME='QIKVRT' BORDER='thin' CAPTION='yes' SHOWINTASKBAR='yes' SINGLEINSTANCE='yes' SYSMENU='yes' SCROLL='no' WINDOWSTATE='normal'/>" +
    "<script language='javascript'>\n" +
    "function done(){var fso=new ActiveXObject('Scripting.FileSystemObject');var f=fso.CreateTextFile('" + htaEscapeForJsString(outPath) + "',true);f.Write(document.getElementById('pw').value);f.Close();window.close();}\n" +
    "function cancel(){window.close();}\n" +
    "function init(){window.resizeTo(760,250);document.getElementById('pw').focus();}\n" +
    "document.onkeydown=function(){if(event.keyCode==13)done(); if(event.keyCode==27)cancel();};\n" +
    "</script></head><body onload='init()' style='font-family:Segoe UI,Arial,sans-serif;font-size:14px;margin:20px;'>" +
    "<div><b>" + htaEscapeForJsString(label) + "</b></div>" +
    "<p>The token is masked and will not be printed to the console. It is used in memory for this release-freeze operation only.</p>" +
    "<input id='pw' type='password' style='width:690px;font-size:16px;' autocomplete='off'/>" +
    "<p><button onclick='done()' style='font-size:14px;'>OK</button> <button onclick='cancel()' style='font-size:14px;'>Cancel</button></p>" +
    "</body></html>";
  var h = fso.CreateTextFile(htaPath, true);
  h.Write(html);
  h.Close();
  out("MASKED_TOKEN_PROMPT opened for " + label);
  shell.Run("mshta.exe \"" + htaPath + "\"", 1, true);
  try { if (fso.FileExists(htaPath)) fso.DeleteFile(htaPath, true); } catch (del0) {}
  if (!fso.FileExists(outPath)) { out("BLOCK TOKEN_INPUT_CANCELLED for " + label); WScript.Quit(32); }
  var tf = fso.OpenTextFile(outPath, 1);
  var tok = tf.ReadAll();
  tf.Close();
  try { fso.DeleteFile(outPath, true); } catch (del1) {}
  tok = trim(tok);
  if (tok === "") { out("BLOCK EMPTY_TOKEN for " + label); WScript.Quit(33); }
  out("MASKED_TOKEN_RECEIVED " + label);
  return tok;
}

function httpRequest(method, url, token, body) {
  var req = null;
  try { req = new ActiveXObject("MSXML2.ServerXMLHTTP.6.0"); } catch (e1) {
    try { req = new ActiveXObject("MSXML2.ServerXMLHTTP"); } catch (e2) { req = new ActiveXObject("MSXML2.XMLHTTP"); }
  }
  req.open(method, url, false);
  req.setRequestHeader("User-Agent", "QIKVRT-4AU2-Release-Freeze-Installer");
  req.setRequestHeader("Accept", "application/vnd.github+json");
  req.setRequestHeader("X-GitHub-Api-Version", "2022-11-28");
  if (token && token !== "") req.setRequestHeader("Authorization", "Bearer " + token);
  if (body !== null && body !== undefined) req.setRequestHeader("Content-Type", "application/json; charset=utf-8");
  try { req.send(body === null || body === undefined ? null : body); }
  catch (ex) { return {status:0, text:String(ex)}; }
  return {status:req.status, text:req.responseText};
}

function utf8Base64(text) {
  var stream = new ActiveXObject("ADODB.Stream");
  stream.Type = 2;
  stream.Charset = "utf-8";
  stream.Open();
  stream.WriteText(String(text));
  stream.Position = 0;
  stream.Type = 1;
  var bytes = stream.Read();
  stream.Close();
  var dom = new ActiveXObject("MSXML2.DOMDocument.6.0");
  var elem = dom.createElement("b64");
  elem.dataType = "bin.base64";
  elem.nodeTypedValue = bytes;
  return String(elem.text).replace(/[\r\n]/g, "");
}

function getExistingSha(repo, branch, targetPath, token) {
  var url = "https://api.github.com/repos/" + repo + "/contents/" + apiPathEncode(targetPath) + "?ref=" + encodeURIComponent(branch);
  var res = httpRequest("GET", url, token, null);
  if (res.status === 404) return "";
  if (res.status !== 200) {
    out("BLOCK GET_EXISTING_FAILED repo=" + repo + " path=" + targetPath + " http=" + res.status);
    out(res.text.substring(0, 600));
    WScript.Quit(41);
  }
  var m = /"sha"\s*:\s*"([^"]+)"/.exec(res.text);
  return m ? m[1] : "";
}

function uploadText(repo, branch, targetPath, text, token, message) {
  var b64 = utf8Base64(text);
  var sha = getExistingSha(repo, branch, targetPath, token);
  var body = "{\"message\":\"" + jsonEscape(message) + "\",\"branch\":\"" + jsonEscape(branch) + "\",\"content\":\"" + b64 + "\"";
  if (sha !== "") body += ",\"sha\":\"" + jsonEscape(sha) + "\"";
  body += "}";
  var url = "https://api.github.com/repos/" + repo + "/contents/" + apiPathEncode(targetPath);
  var res = httpRequest("PUT", url, token, body);
  if (res.status !== 200 && res.status !== 201) {
    out("BLOCK UPLOAD_FAILED repo=" + repo + " path=" + targetPath + " http=" + res.status);
    out(res.text.substring(0, 800));
    WScript.Quit(42);
  }
  out("PASS upload " + repo + " " + targetPath);
}

function parseJsonField(text, field) {
  var re = new RegExp('"' + field + '"\\s*:\\s*"([^"]+)"');
  var m = re.exec(text);
  return m ? m[1] : "";
}

function getBranchHeadSha(repo, branch, token) {
  var url = "https://api.github.com/repos/" + repo + "/git/ref/heads/" + encodeURIComponent(branch);
  var res = httpRequest("GET", url, token, null);
  if (res.status !== 200) {
    out("BLOCK GET_BRANCH_HEAD_FAILED repo=" + repo + " branch=" + branch + " http=" + res.status);
    out(res.text.substring(0, 800));
    WScript.Quit(61);
  }
  var m = /"object"\s*:\s*\{[^\}]*"sha"\s*:\s*"([^"]+)"/.exec(res.text);
  if (!m) m = /"sha"\s*:\s*"([0-9a-f]{40})"/.exec(res.text);
  if (!m) { out("BLOCK BRANCH_SHA_PARSE_FAILED repo=" + repo); WScript.Quit(62); }
  return m[1];
}

function releaseExists(repo, tag, token) {
  var url = "https://api.github.com/repos/" + repo + "/releases/tags/" + encodeURIComponent(tag);
  var res = httpRequest("GET", url, token, null);
  if (res.status === 200) return true;
  if (res.status === 404) return false;
  out("BLOCK RELEASE_LOOKUP_FAILED repo=" + repo + " tag=" + tag + " http=" + res.status);
  out(res.text.substring(0, 600));
  WScript.Quit(63);
}

function createRelease(repo, tag, targetSha, name, bodyText, token, draft, prerelease) {
  if (releaseExists(repo, tag, token)) {
    out("BLOCK RELEASE_ALREADY_EXISTS_NO_TAG_MOVE repo=" + repo + " tag=" + tag);
    out("Choose a new tag or keep the existing release. This installer will not move or overwrite release history.");
    WScript.Quit(64);
  }
  var body = "{\"tag_name\":\"" + jsonEscape(tag) + "\",\"target_commitish\":\"" + jsonEscape(targetSha) + "\",\"name\":\"" + jsonEscape(name) + "\",\"body\":\"" + jsonEscape(bodyText) + "\",\"draft\":" + (draft ? "true" : "false") + ",\"prerelease\":" + (prerelease ? "true" : "false") + "}";
  var url = "https://api.github.com/repos/" + repo + "/releases";
  var res = httpRequest("POST", url, token, body);
  if (res.status !== 201) {
    out("BLOCK RELEASE_CREATE_FAILED repo=" + repo + " tag=" + tag + " http=" + res.status);
    out(res.text.substring(0, 1000));
    WScript.Quit(65);
  }
  var html = parseJsonField(res.text, "html_url");
  out("GITHUB_RELEASE_CREATE PASS " + repo + " tag=" + tag + " target_sha=" + targetSha);
  if (html !== "") out("GITHUB_RELEASE_URL " + html);
}

function makeReleaseJson(role, repo, branch, tag, runId, publicRunId, status) {
  return "{\n" +
    "  \"qikvrt_event\": \"4AU1_PRODUCTIZATION_RELEASE_FREEZE\",\n" +
    "  \"kit_version\": \"" + VERSION + "\",\n" +
    "  \"role\": \"" + role + "\",\n" +
    "  \"repository\": \"" + repo + "\",\n" +
    "  \"branch\": \"" + branch + "\",\n" +
    "  \"tag\": \"" + tag + "\",\n" +
    "  \"installer_run_id\": \"" + runId + "\",\n" +
    "  \"referenced_productization_run_id\": \"" + publicRunId + "\",\n" +
    "  \"status\": \"" + status + "\",\n" +
    "  \"created_utc\": \"" + isoUtc() + "\",\n" +
    "  \"boundaries\": {\n" +
    "    \"no_existing_tag_move\": true,\n" +
    "    \"no_global_scanning\": true,\n" +
    "    \"no_self_propagation\": true,\n" +
    "    \"no_embedded_token\": true,\n" +
    "    \"masked_token_input\": true\n" +
    "  }\n" +
    "}\n";
}

function makeReleaseMd(role, repo, branch, tag, runId, publicRunId) {
  return "# QIK-VRT 4AU1 Productization Release Freeze - " + role + "\n\n" +
    "```text\n" +
    "repository: " + repo + "\n" +
    "branch: " + branch + "\n" +
    "release_tag: " + tag + "\n" +
    "installer_run_id: " + runId + "\n" +
    "referenced_productization_run_id: " + publicRunId + "\n" +
    "status: PREPARED_FOR_GITHUB_RELEASE\n" +
    "```\n\n" +
    "This file freezes the public 4AU1 productization hardening result as a release-ready repository state.\n\n" +
    "Boundaries:\n\n" +
    "```text\n" +
    "NO_EXISTING_TAG_MOVE      true\n" +
    "NO_GLOBAL_SCANNING        true\n" +
    "NO_SELF_PROPAGATION       true\n" +
    "NO_EMBEDDED_TOKEN         true\n" +
    "MASKED_TOKEN_INPUT        true\n" +
    "FULL_BYTE_REHASH_HERE     not executed by installer\n" +
    "```\n";
}

function makeReleaseBody(role, repo, branch, tag, targetSha, runId, publicRunId) {
  return "QIK-VRT 4AU1 Productization Release Freeze (" + role + ")\n\n" +
    "Repository: " + repo + "\n" +
    "Branch: " + branch + "\n" +
    "Tag: " + tag + "\n" +
    "Target commit SHA: " + targetSha + "\n" +
    "Installer run id: " + runId + "\n" +
    "Referenced public productization run id: " + publicRunId + "\n\n" +
    "Scope:\n" +
    "- freezes the 4AU1 productization hardening state into a public GitHub Release\n" +
    "- preserves autonomous Seed/Node mesh boundaries\n" +
    "- does not claim full byte-level non-regression beyond the published evidence files\n\n" +
    "Expected evidence paths:\n" +
    "- release/qikvrt_4au1/QIKVRT_RELEASE_FREEZE_" + upper(role) + ".json\n" +
    "- release/qikvrt_4au1/QIKVRT_RELEASE_FREEZE_" + upper(role) + ".md\n" +
    "- evidence/release_freeze/runs/" + runId + "_" + role + ".json\n\n" +
    "QIK-VRT status:\n" +
    "PUBLIC_PRODUCTIZATION_RELEASE_FREEZE = PASS after this release is visible.\n" +
    "NO_FALSE_FULL_BYTE_PASS = PASS.\n";
}

function uploadFreezeFiles(role, repo, branch, tag, runId, publicRunId, token) {
  var roleUpper = upper(role);
  var json = makeReleaseJson(role, repo, branch, tag, runId, publicRunId, "PREPARED_FOR_GITHUB_RELEASE");
  var md = makeReleaseMd(role, repo, branch, tag, runId, publicRunId);
  var doc = "# QIK-VRT 4AU1 Productization Release\n\n" + md;
  uploadText(repo, branch, "release/qikvrt_4au1/QIKVRT_RELEASE_FREEZE_" + roleUpper + ".json", json, token, "QIKVRT 4AU2 release freeze json " + role);
  uploadText(repo, branch, "release/qikvrt_4au1/QIKVRT_RELEASE_FREEZE_" + roleUpper + ".md", md, token, "QIKVRT 4AU2 release freeze md " + role);
  uploadText(repo, branch, "evidence/release_freeze/runs/" + runId + "_" + role + ".json", json, token, "QIKVRT 4AU2 release freeze evidence " + role);
  uploadText(repo, branch, "docs/QIKVRT_4AU1_PRODUCTIZATION_RELEASE_" + roleUpper + ".md", doc, token, "QIKVRT 4AU2 productization release doc " + role);
}

out("QIKVRT V2.13.4AU2 Productization Release Freeze Installer");
out("No visible token prompt. Creates release-freeze evidence and GitHub Releases for Seed and Node.");
var acc = promptLine("Accept copyright and license? Type JA or YES", "");
if (!ynAccept(acc)) { out("BLOCK COPYRIGHT_AND_LICENSE_NOT_ACCEPTED"); WScript.Quit(11); }
var auth = promptLine("Confirm Product Owner release authorization? Type JA or YES", "");
if (!ynAccept(auth)) { out("BLOCK PRODUCT_OWNER_RELEASE_NOT_AUTHORIZED"); WScript.Quit(12); }
var seedRepo = promptLine("Seed repository", SEED_DEFAULT);
var nodeRepo = promptLine("Node repository", NODE_DEFAULT);
var seedBranch = promptLine("Seed branch", BRANCH_DEFAULT);
var nodeBranch = promptLine("Node branch", BRANCH_DEFAULT);
var publicRunId = promptLine("Referenced public 4AU1 PASS run id", PUBLIC_RUN_DEFAULT);
var runId = promptLine("Release-freeze installer run id", nowRunId());
var seedTag = promptLine("Seed release tag", SEED_TAG_DEFAULT);
var nodeTag = promptLine("Node release tag", NODE_TAG_DEFAULT);
var draftAnswer = upper(promptLine("Create releases as drafts? YES or NO", "NO"));
var draft = (draftAnswer === "YES" || draftAnswer === "JA" || draftAnswer === "Y" || draftAnswer === "J");
out("Seed release target: " + seedRepo + " @ " + seedBranch + " tag=" + seedTag);
out("Node release target: " + nodeRepo + " @ " + nodeBranch + " tag=" + nodeTag);
out("Referenced public run: " + publicRunId);
out("Release-freeze installer run id: " + runId);
out("Mode DRYRUN performs local planning only and requires no token/network.");
var mode = upper(promptLine("Mode: DRYRUN or RELEASE", "DRYRUN"));
if (mode !== "DRYRUN" && mode !== "RELEASE") { out("BLOCK invalid mode"); WScript.Quit(13); }
if (mode === "DRYRUN") {
  out("DRYRUN seed release files=4 tag=" + seedTag);
  out("DRYRUN node release files=4 tag=" + nodeTag);
  out("DRYRUN GitHub releases would be created after evidence upload. Existing releases/tags will not be moved.");
  out("QIKVRT_4AU2_RELEASE_FREEZE_FINAL PASS mode=DRYRUN");
  WScript.Quit(0);
}

out("RELEASE mode selected. Tokens are requested in masked local dialogs.");
out("SEED token scope needed for " + seedRepo + ": Contents read/write and Releases write via repository contents/release permissions.");
var seedToken = readSecretHidden("SEED TOKEN for repository " + seedRepo);
var same = upper(promptLine("Use the same token also for NODE repository " + nodeRepo + "? Type YES only if this token has write access to that repo", "NO"));
var nodeToken = "";
if (same === "YES" || same === "JA" || same === "Y" || same === "J") {
  nodeToken = seedToken;
  out("TOKEN_REUSE_FOR_NODE explicitly accepted");
} else {
  out("NODE token scope needed for " + nodeRepo + ": Contents read/write and Releases write via repository contents/release permissions.");
  nodeToken = readSecretHidden("NODE TOKEN for repository " + nodeRepo);
}
var final = upper(promptLine("FINAL REMOTE RELEASE CONFIRMATION for BOTH repos. Type RELEASE", ""));
if (final !== "RELEASE") { out("BLOCK FINAL_RELEASE_CONFIRMATION_NOT_GIVEN"); WScript.Quit(14); }

out("QIKVRT_UPLOAD_RELEASE_FREEZE_EVIDENCE role=seed repo=" + seedRepo + " branch=" + seedBranch);
uploadFreezeFiles("seed", seedRepo, seedBranch, seedTag, runId, publicRunId, seedToken);
out("QIKVRT_UPLOAD_RELEASE_FREEZE_EVIDENCE role=node repo=" + nodeRepo + " branch=" + nodeBranch);
uploadFreezeFiles("node", nodeRepo, nodeBranch, nodeTag, runId, publicRunId, nodeToken);

var seedSha = getBranchHeadSha(seedRepo, seedBranch, seedToken);
var nodeSha = getBranchHeadSha(nodeRepo, nodeBranch, nodeToken);
out("BRANCH_HEAD_SHA PASS " + seedRepo + " " + seedBranch + " " + seedSha);
out("BRANCH_HEAD_SHA PASS " + nodeRepo + " " + nodeBranch + " " + nodeSha);

createRelease(seedRepo, seedTag, seedSha, "QIK-VRT 4AU1 Seed Productization Release", makeReleaseBody("seed", seedRepo, seedBranch, seedTag, seedSha, runId, publicRunId), seedToken, draft, false);
createRelease(nodeRepo, nodeTag, nodeSha, "QIK-VRT 4AU1 Node Productization Release", makeReleaseBody("node", nodeRepo, nodeBranch, nodeTag, nodeSha, runId, publicRunId), nodeToken, draft, false);

out("QIKVRT_PRODUCTIZATION_RELEASE_FREEZE_SEQUENCE PASS run_id=" + runId);
out("QIKVRT_4AU2_RELEASE_FREEZE_FINAL PASS mode=RELEASE");
WScript.Quit(0);
