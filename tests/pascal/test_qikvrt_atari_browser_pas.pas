{ SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 }
program TestQikVrtAtariBrowserPas;

uses QikVrtAtariBrowserPas;

var
  Failures: Integer;

procedure Expect(Condition: Boolean; const NameValue: string);
begin
  if not Condition then
  begin
    WriteLn('FAIL: ', NameValue);
    Inc(Failures);
  end;
end;

procedure TestUrlAndRequest;
var
  Url: TBrowserUrl;
  RequestValue: TRequestBuffer;
  Status: TBrowserStatus;
begin
  Status := ParseUrl('http://127.0.0.1:8771/a/b?x=1#ignored', Url);
  Expect(Status = bsOk, 'parse bounded URL');
  Expect(Url.Host = '127.0.0.1', 'parse host');
  Expect(Url.Port = 8771, 'parse port');
  Expect(Url.Path = '/a/b?x=1', 'strip fragment');
  Expect(UrlIsLoopback(Url), 'loopback marker');

  Status := BuildHttpGet(Url, RequestValue);
  Expect(Status = bsOk, 'build request');
  Expect(RequestStartsWith(RequestValue, 'GET /a/b?x=1 HTTP/1.0' + #13#10),
    'request line');
  Expect(RequestContains(RequestValue, 'Host: 127.0.0.1:8771' + #13#10),
    'host header');
  Expect(RequestContains(RequestValue, 'Connection: close' + #13#10),
    'connection close');

  Status := ParseUrl('https://example.org/', Url);
  Expect(Status = bsUnsupportedScheme,
    'fail closed without TLS implementation');
end;

procedure TestHttpAndHtml;
var
  ResponseBuffer: TLargeBuffer;
  Parsed: THttpResponse;
  DocumentValue: TBrowserDocument;
  Status: TBrowserStatus;
begin
  ClearLargeBuffer(ResponseBuffer);
  Expect(AppendLargeBuffer(ResponseBuffer, 'HTTP/1.0 200 OK' + #13#10),
    'append status line');
  Expect(AppendLargeBuffer(ResponseBuffer, 'Content-Type: text/html' + #13#10),
    'append content type');
  Expect(AppendLargeBuffer(ResponseBuffer, 'Content-Length: 192' + #13#10#13#10),
    'append header terminator');
  Expect(AppendLargeBuffer(ResponseBuffer,
    '<!doctype html><html><head><title>QIK &amp; VRT</title>'),
    'append title');
  Expect(AppendLargeBuffer(ResponseBuffer,
    '<style>hidden style</style><script>hidden script</script></head>'),
    'append suppressed content');
  Expect(AppendLargeBuffer(ResponseBuffer,
    '<body><h1>Atari Browser</h1><p>Hello &lt;world&gt;.</p>'),
    'append visible content');
  Expect(AppendLargeBuffer(ResponseBuffer,
    '<ul><li>One</li><li><a href="/two">Two</a></li></ul>'),
    'append link');
  Expect(AppendLargeBuffer(ResponseBuffer,
    '<pre>A  B' + #10 + 'C</pre></body></html>'),
    'append preformatted content');

  Status := ParseHttpResponse(ResponseBuffer, ResponseBuffer.Length, Parsed);
  Expect(Status = bsOk, 'parse HTTP response');
  Expect(Parsed.StatusCode = 200, 'status code');
  Expect(Parsed.BodyLength > 0, 'body length');

  Status := RenderHtml(
    ResponseBuffer,
    Parsed.BodyOffset,
    Parsed.BodyLength,
    DocumentValue
  );
  Expect(Status = bsOk, 'render HTML');
  Expect(DocumentValue.Title = 'QIK & VRT', 'title text');
  Expect(DocumentTextContains(DocumentValue, 'Atari Browser'), 'heading text');
  Expect(DocumentTextContains(DocumentValue, 'Hello <world>.'), 'entity decode');
  Expect(not DocumentTextContains(DocumentValue, 'hidden script'),
    'script suppressed');
  Expect(not DocumentTextContains(DocumentValue, 'hidden style'),
    'style suppressed');
  Expect(DocumentValue.LinkCount = 1, 'link count');
  Expect(DocumentValue.Links[1].Href = '/two', 'link href');
  Expect(DocumentValue.Links[1].Text = 'Two', 'link label');
  Expect(DocumentTextContains(DocumentValue, 'A  B' + #10 + 'C'),
    'pre whitespace preserved');
  Expect(not DocumentValue.Truncated, 'document not truncated');
end;

procedure TestFailClosedInputs;
var
  BufferValue: TLargeBuffer;
  Response: THttpResponse;
  DocumentValue: TBrowserDocument;
  Status: TBrowserStatus;
begin
  ClearLargeBuffer(BufferValue);
  AppendLargeBuffer(BufferValue, 'not http');
  Status := ParseHttpResponse(BufferValue, BufferValue.Length, Response);
  Expect(Status = bsInvalidHttp, 'invalid HTTP blocked');

  ClearLargeBuffer(BufferValue);
  AppendLargeBuffer(BufferValue, '<p unterminated');
  Status := RenderHtml(BufferValue, 1, BufferValue.Length, DocumentValue);
  Expect(Status = bsInvalidHtml, 'unterminated tag blocked');
end;

begin
  Failures := 0;
  TestUrlAndRequest;
  TestHttpAndHtml;
  TestFailClosedInputs;
  if Failures <> 0 then
  begin
    WriteLn('QIKVRT Atari browser Pascal: ', Failures, ' failure(s)');
    Halt(1);
  end;
  WriteLn('QIKVRT Atari browser Pascal: PASS (bounded dialect bridge)');
end.
