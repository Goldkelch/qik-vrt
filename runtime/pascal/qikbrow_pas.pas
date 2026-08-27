{ SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 }
program QikBrowPas;

uses QikVrtAtariBrowserPas;

var
  Url: TBrowserUrl;
  RequestValue: TRequestBuffer;
  Status: TBrowserStatus;

begin
  if ParamCount <> 1 then
  begin
    WriteLn('usage: qikbrow_pas http://host[:port]/path');
    Halt(2);
  end;
  Status := ParseUrl(ParamStr(1), Url);
  if Status <> bsOk then
  begin
    WriteLn('BLOCK ', StatusName(Status));
    Halt(3);
  end;
  Status := BuildHttpGet(Url, RequestValue);
  if Status <> bsOk then
  begin
    WriteLn('BLOCK ', StatusName(Status));
    Halt(4);
  end;
  WriteLn('HOST=', Url.Host);
  WriteLn('PORT=', Url.Port);
  WriteLn('PATH=', Url.Path);
  if Url.Loopback then
    WriteLn('LOOPBACK=true')
  else
    WriteLn('LOOPBACK=false');
  WriteRequest(RequestValue);
end.
