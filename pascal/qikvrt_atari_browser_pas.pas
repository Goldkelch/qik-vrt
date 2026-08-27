{ SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 }
{ Copyright 2026 Ingolf Lohmann. }
unit QikVrtAtariBrowserPas;

interface

const
  HostCapacity = 63;
  PathCapacity = 255;
  TextCapacity = 4096;
  TitleCapacity = 127;
  LinkCapacity = 16;
  LinkTextCapacity = 127;
  RequestCapacity = 512;
  ResponseCapacity = 8192;

type
  TBrowserStatus = (
    bsOk,
    bsBadArgument,
    bsUnsupportedScheme,
    bsInvalidUrl,
    bsBufferTooSmall,
    bsInvalidHttp,
    bsInvalidHtml
  );

  THostString = string[HostCapacity];
  TPathString = string[PathCapacity];
  TTitleString = string[TitleCapacity];
  TLinkTextString = string[LinkTextCapacity];
  TStatusString = string[31];

  TBrowserUrl = record
    Host: THostString;
    Port: Word;
    Path: TPathString;
    Loopback: Boolean;
  end;

  TLargeBuffer = record
    Data: array[1..ResponseCapacity] of Char;
    Length: Word;
  end;

  TRequestBuffer = record
    Data: array[1..RequestCapacity] of Char;
    Length: Word;
  end;

  THttpResponse = record
    StatusCode: Integer;
    BodyOffset: Word;
    BodyLength: Word;
  end;

  TBrowserLink = record
    Href: TPathString;
    Text: TLinkTextString;
  end;

  TBrowserDocument = record
    Title: TTitleString;
    Text: array[1..TextCapacity] of Char;
    TextLength: Word;
    Links: array[1..LinkCapacity] of TBrowserLink;
    LinkCount: Byte;
    Truncated: Boolean;
  end;

procedure ClearLargeBuffer(var BufferValue: TLargeBuffer);
function AppendLargeBuffer(var BufferValue: TLargeBuffer; const Value: string): Boolean;
function ParseUrl(const Input: string; var Url: TBrowserUrl): TBrowserStatus;
function BuildHttpGet(const Url: TBrowserUrl; var Output: TRequestBuffer): TBrowserStatus;
function ParseHttpResponse(
  const Input: TLargeBuffer;
  InputLength: Word;
  var Response: THttpResponse
): TBrowserStatus;
function RenderHtml(
  const Input: TLargeBuffer;
  Offset: Word;
  InputLength: Word;
  var DocumentValue: TBrowserDocument
): TBrowserStatus;
function UrlIsLoopback(const Url: TBrowserUrl): Boolean;
function StatusName(Status: TBrowserStatus): TStatusString;
function RequestStartsWith(const BufferValue: TRequestBuffer; const Value: string): Boolean;
function RequestContains(const BufferValue: TRequestBuffer; const Value: string): Boolean;
function DocumentTextContains(const DocumentValue: TBrowserDocument; const Value: string): Boolean;
procedure WriteRequest(const BufferValue: TRequestBuffer);
procedure WriteDocumentText(const DocumentValue: TBrowserDocument);

implementation

function IsSpaceChar(Value: Char): Boolean;
begin
  IsSpaceChar := (Value = ' ') or (Value = #9) or (Value = #10) or
    (Value = #13) or (Value = #12);
end;

function IsDigitChar(Value: Char): Boolean;
begin
  IsDigitChar := (Value >= '0') and (Value <= '9');
end;

function IsAlphaNumChar(Value: Char): Boolean;
begin
  IsAlphaNumChar := ((Value >= 'A') and (Value <= 'Z')) or
    ((Value >= 'a') and (Value <= 'z')) or IsDigitChar(Value);
end;

function LowerChar(Value: Char): Char;
begin
  if (Value >= 'A') and (Value <= 'Z') then
    LowerChar := Chr(Ord(Value) + Ord('a') - Ord('A'))
  else
    LowerChar := Value;
end;

function EqI(const LeftValue, RightValue: string): Boolean;
var
  IndexValue: Integer;
begin
  EqI := False;
  if Length(LeftValue) <> Length(RightValue) then
    Exit;
  for IndexValue := 1 to Length(LeftValue) do
    if LowerChar(LeftValue[IndexValue]) <> LowerChar(RightValue[IndexValue]) then
      Exit;
  EqI := True;
end;

function StartsWithI(const Value, PrefixValue: string): Boolean;
var
  IndexValue: Integer;
begin
  StartsWithI := False;
  if Length(Value) < Length(PrefixValue) then
    Exit;
  for IndexValue := 1 to Length(PrefixValue) do
    if LowerChar(Value[IndexValue]) <> LowerChar(PrefixValue[IndexValue]) then
      Exit;
  StartsWithI := True;
end;

procedure ClearLargeBuffer(var BufferValue: TLargeBuffer);
begin
  FillChar(BufferValue, SizeOf(BufferValue), 0);
end;

function AppendLargeBuffer(var BufferValue: TLargeBuffer; const Value: string): Boolean;
var
  IndexValue: Integer;
begin
  AppendLargeBuffer := False;
  if LongInt(BufferValue.Length) + Length(Value) > ResponseCapacity then
    Exit;
  for IndexValue := 1 to Length(Value) do
  begin
    Inc(BufferValue.Length);
    BufferValue.Data[BufferValue.Length] := Value[IndexValue];
  end;
  AppendLargeBuffer := True;
end;

procedure ClearRequest(var BufferValue: TRequestBuffer);
begin
  FillChar(BufferValue, SizeOf(BufferValue), 0);
end;

function AppendRequestChar(var BufferValue: TRequestBuffer; Value: Char): Boolean;
begin
  AppendRequestChar := False;
  if BufferValue.Length >= RequestCapacity then
    Exit;
  Inc(BufferValue.Length);
  BufferValue.Data[BufferValue.Length] := Value;
  AppendRequestChar := True;
end;

function AppendRequestString(var BufferValue: TRequestBuffer; const Value: string): Boolean;
var
  IndexValue: Integer;
begin
  AppendRequestString := False;
  if LongInt(BufferValue.Length) + Length(Value) > RequestCapacity then
    Exit;
  for IndexValue := 1 to Length(Value) do
    if not AppendRequestChar(BufferValue, Value[IndexValue]) then
      Exit;
  AppendRequestString := True;
end;

function ParseUrl(const Input: string; var Url: TBrowserUrl): TBrowserStatus;
var
  AuthorityStart: Integer;
  AuthorityEnd: Integer;
  HostEnd: Integer;
  ColonPosition: Integer;
  FragmentPosition: Integer;
  Cursor: Integer;
  PortValue: LongInt;
  PortText: string[5];
  HostText: string[255];
  PathText: string[255];
  CurrentChar: Char;
begin
  FillChar(Url, SizeOf(Url), 0);
  if Length(Input) = 0 then
  begin
    ParseUrl := bsBadArgument;
    Exit;
  end;
  if not StartsWithI(Input, 'http://') then
  begin
    ParseUrl := bsUnsupportedScheme;
    Exit;
  end;

  AuthorityStart := 8;
  AuthorityEnd := AuthorityStart;
  while AuthorityEnd <= Length(Input) do
  begin
    CurrentChar := Input[AuthorityEnd];
    if (CurrentChar = '/') or (CurrentChar = '?') or (CurrentChar = '#') then
      Break;
    if (Ord(CurrentChar) <= 32) or (Ord(CurrentChar) = 127) or
      (CurrentChar = '\') or (CurrentChar = '@') then
    begin
      ParseUrl := bsInvalidUrl;
      Exit;
    end;
    Inc(AuthorityEnd);
  end;
  if AuthorityEnd = AuthorityStart then
  begin
    ParseUrl := bsInvalidUrl;
    Exit;
  end;

  ColonPosition := 0;
  for Cursor := AuthorityStart to AuthorityEnd - 1 do
    if Input[Cursor] = ':' then
      ColonPosition := Cursor;
  if ColonPosition = 0 then
    HostEnd := AuthorityEnd
  else
    HostEnd := ColonPosition;

  HostText := Copy(Input, AuthorityStart, HostEnd - AuthorityStart);
  if (Length(HostText) = 0) or (Length(HostText) > HostCapacity) then
  begin
    if Length(HostText) > HostCapacity then
      ParseUrl := bsBufferTooSmall
    else
      ParseUrl := bsInvalidUrl;
    Exit;
  end;
  Url.Host := HostText;
  Url.Port := 80;

  if ColonPosition <> 0 then
  begin
    PortText := Copy(Input, ColonPosition + 1, AuthorityEnd - ColonPosition - 1);
    if Length(PortText) = 0 then
    begin
      ParseUrl := bsInvalidUrl;
      Exit;
    end;
    PortValue := 0;
    for Cursor := 1 to Length(PortText) do
    begin
      if not IsDigitChar(PortText[Cursor]) then
      begin
        ParseUrl := bsInvalidUrl;
        Exit;
      end;
      PortValue := PortValue * 10 + Ord(PortText[Cursor]) - Ord('0');
      if PortValue > 65535 then
      begin
        ParseUrl := bsInvalidUrl;
        Exit;
      end;
    end;
    if PortValue = 0 then
    begin
      ParseUrl := bsInvalidUrl;
      Exit;
    end;
    Url.Port := PortValue;
  end;

  FragmentPosition := AuthorityEnd;
  while (FragmentPosition <= Length(Input)) and
    (Input[FragmentPosition] <> '#') do
  begin
    CurrentChar := Input[FragmentPosition];
    if (Ord(CurrentChar) <= 31) or (CurrentChar = ' ') then
    begin
      ParseUrl := bsInvalidUrl;
      Exit;
    end;
    Inc(FragmentPosition);
  end;

  if AuthorityEnd > Length(Input) then
    PathText := '/'
  else if Input[AuthorityEnd] = '#' then
    PathText := '/'
  else if Input[AuthorityEnd] = '?' then
    PathText := '/' + Copy(Input, AuthorityEnd, FragmentPosition - AuthorityEnd)
  else
    PathText := Copy(Input, AuthorityEnd, FragmentPosition - AuthorityEnd);

  if Length(PathText) > PathCapacity then
  begin
    ParseUrl := bsBufferTooSmall;
    Exit;
  end;
  if (Length(PathText) = 0) or (PathText[1] <> '/') then
  begin
    ParseUrl := bsInvalidUrl;
    Exit;
  end;
  Url.Path := PathText;
  Url.Loopback := EqI(Url.Host, 'localhost') or EqI(Url.Host, '127.0.0.1');
  ParseUrl := bsOk;
end;

function BuildHttpGet(const Url: TBrowserUrl; var Output: TRequestBuffer): TBrowserStatus;
var
  PortText: string[5];
begin
  ClearRequest(Output);
  if (Length(Url.Host) = 0) or (Length(Url.Path) = 0) or
    (Url.Path[1] <> '/') or (Url.Port = 0) then
  begin
    BuildHttpGet := bsInvalidUrl;
    Exit;
  end;
  if not AppendRequestString(Output, 'GET ') or
    not AppendRequestString(Output, Url.Path) or
    not AppendRequestString(Output, ' HTTP/1.0' + #13#10 + 'Host: ') or
    not AppendRequestString(Output, Url.Host) then
  begin
    BuildHttpGet := bsBufferTooSmall;
    Exit;
  end;
  if Url.Port <> 80 then
  begin
    Str(Url.Port, PortText);
    if not AppendRequestChar(Output, ':') or
      not AppendRequestString(Output, PortText) then
    begin
      BuildHttpGet := bsBufferTooSmall;
      Exit;
    end;
  end;
  if not AppendRequestString(Output,
    #13#10 + 'Connection: close' + #13#10 +
    'User-Agent: QIKVRT-Atari-Pascal/1' + #13#10 +
    'Accept: text/html,text/plain' + #13#10#13#10) then
  begin
    BuildHttpGet := bsBufferTooSmall;
    Exit;
  end;
  BuildHttpGet := bsOk;
end;

function BufferMatchesAt(
  const BufferValue: TLargeBuffer;
  PositionValue: Word;
  const Value: string
): Boolean;
var
  IndexValue: Integer;
begin
  BufferMatchesAt := False;
  if (PositionValue = 0) or
    (LongInt(PositionValue) + Length(Value) - 1 > BufferValue.Length) then
    Exit;
  for IndexValue := 1 to Length(Value) do
    if BufferValue.Data[PositionValue + IndexValue - 1] <> Value[IndexValue] then
      Exit;
  BufferMatchesAt := True;
end;

function ParseHttpResponse(
  const Input: TLargeBuffer;
  InputLength: Word;
  var Response: THttpResponse
): TBrowserStatus;
var
  Cursor: Word;
  BodyOffsetValue: Word;
begin
  FillChar(Response, SizeOf(Response), 0);
  if (InputLength < 12) or (InputLength > Input.Length) then
  begin
    ParseHttpResponse := bsInvalidHttp;
    Exit;
  end;
  if not BufferMatchesAt(Input, 1, 'HTTP/1.') then
  begin
    ParseHttpResponse := bsInvalidHttp;
    Exit;
  end;
  if not IsDigitChar(Input.Data[10]) or
    not IsDigitChar(Input.Data[11]) or
    not IsDigitChar(Input.Data[12]) then
  begin
    ParseHttpResponse := bsInvalidHttp;
    Exit;
  end;
  Response.StatusCode :=
    (Ord(Input.Data[10]) - Ord('0')) * 100 +
    (Ord(Input.Data[11]) - Ord('0')) * 10 +
    Ord(Input.Data[12]) - Ord('0');

  BodyOffsetValue := 0;
  Cursor := 1;
  while Cursor + 3 <= InputLength do
  begin
    if (Input.Data[Cursor] = #13) and
      (Input.Data[Cursor + 1] = #10) and
      (Input.Data[Cursor + 2] = #13) and
      (Input.Data[Cursor + 3] = #10) then
    begin
      BodyOffsetValue := Cursor + 4;
      Break;
    end;
    Inc(Cursor);
  end;
  if BodyOffsetValue = 0 then
  begin
    Cursor := 1;
    while Cursor + 1 <= InputLength do
    begin
      if (Input.Data[Cursor] = #10) and (Input.Data[Cursor + 1] = #10) then
      begin
        BodyOffsetValue := Cursor + 2;
        Break;
      end;
      Inc(Cursor);
    end;
  end;
  if BodyOffsetValue = 0 then
  begin
    ParseHttpResponse := bsInvalidHttp;
    Exit;
  end;
  Response.BodyOffset := BodyOffsetValue;
  if BodyOffsetValue > InputLength then
    Response.BodyLength := 0
  else
    Response.BodyLength := InputLength - BodyOffsetValue + 1;
  ParseHttpResponse := bsOk;
end;

function TagNameChar(Value: Char): Boolean;
begin
  TagNameChar := IsAlphaNumChar(Value) or (Value = '-') or (Value = ':');
end;

function ParseTagName(
  const TagValue: string;
  var Closing: Boolean;
  var NameValue: string
): Boolean;
var
  Cursor: Integer;
begin
  Closing := False;
  NameValue := '';
  Cursor := 1;
  while (Cursor <= Length(TagValue)) and IsSpaceChar(TagValue[Cursor]) do
    Inc(Cursor);
  if (Cursor <= Length(TagValue)) and (TagValue[Cursor] = '/') then
  begin
    Closing := True;
    Inc(Cursor);
  end;
  while (Cursor <= Length(TagValue)) and IsSpaceChar(TagValue[Cursor]) do
    Inc(Cursor);
  while (Cursor <= Length(TagValue)) and TagNameChar(TagValue[Cursor]) do
  begin
    if Length(NameValue) < 31 then
      NameValue := NameValue + LowerChar(TagValue[Cursor]);
    Inc(Cursor);
  end;
  ParseTagName := Length(NameValue) > 0;
end;

function ExtractAttribute(
  const TagValue, NameValue: string;
  var Output: string
): Boolean;
var
  Cursor: Integer;
  StartValue: Integer;
  AfterName: Integer;
  QuoteValue: Char;
  Candidate: string[31];
begin
  Output := '';
  ExtractAttribute := False;
  Cursor := 1;
  while Cursor <= Length(TagValue) do
  begin
    while (Cursor <= Length(TagValue)) and
      (IsSpaceChar(TagValue[Cursor]) or (TagValue[Cursor] = '/')) do
      Inc(Cursor);
    StartValue := Cursor;
    Candidate := '';
    while (Cursor <= Length(TagValue)) and TagNameChar(TagValue[Cursor]) do
    begin
      if Length(Candidate) < 31 then
        Candidate := Candidate + LowerChar(TagValue[Cursor]);
      Inc(Cursor);
    end;
    if Cursor = StartValue then
    begin
      Inc(Cursor);
    end
    else if EqI(Candidate, NameValue) then
    begin
      AfterName := Cursor;
      while (AfterName <= Length(TagValue)) and IsSpaceChar(TagValue[AfterName]) do
        Inc(AfterName);
      if (AfterName > Length(TagValue)) or (TagValue[AfterName] <> '=') then
        Exit;
      Inc(AfterName);
      while (AfterName <= Length(TagValue)) and IsSpaceChar(TagValue[AfterName]) do
        Inc(AfterName);
      if AfterName > Length(TagValue) then
        Exit;
      QuoteValue := #0;
      if (TagValue[AfterName] = '"') or (TagValue[AfterName] = '''') then
      begin
        QuoteValue := TagValue[AfterName];
        Inc(AfterName);
      end;
      while AfterName <= Length(TagValue) do
      begin
        if ((QuoteValue <> #0) and (TagValue[AfterName] = QuoteValue)) or
          ((QuoteValue = #0) and IsSpaceChar(TagValue[AfterName])) then
          Break;
        if Length(Output) >= 255 then
          Exit;
        Output := Output + TagValue[AfterName];
        Inc(AfterName);
      end;
      ExtractAttribute := Length(Output) > 0;
      Exit;
    end;
  end;
end;

function IsBlockTag(const NameValue: string): Boolean;
begin
  IsBlockTag := EqI(NameValue, 'address') or EqI(NameValue, 'article') or
    EqI(NameValue, 'aside') or EqI(NameValue, 'blockquote') or
    EqI(NameValue, 'br') or EqI(NameValue, 'dd') or
    EqI(NameValue, 'div') or EqI(NameValue, 'dl') or
    EqI(NameValue, 'dt') or EqI(NameValue, 'footer') or
    EqI(NameValue, 'h1') or EqI(NameValue, 'h2') or
    EqI(NameValue, 'h3') or EqI(NameValue, 'h4') or
    EqI(NameValue, 'h5') or EqI(NameValue, 'h6') or
    EqI(NameValue, 'header') or EqI(NameValue, 'hr') or
    EqI(NameValue, 'li') or EqI(NameValue, 'main') or
    EqI(NameValue, 'nav') or EqI(NameValue, 'ol') or
    EqI(NameValue, 'p') or EqI(NameValue, 'pre') or
    EqI(NameValue, 'section') or EqI(NameValue, 'table') or
    EqI(NameValue, 'tr') or EqI(NameValue, 'ul');
end;

function DecodeEntity(
  const Input: TLargeBuffer;
  PositionValue: Word;
  EndPosition: Word;
  var Decoded: Char;
  var Consumed: Word
): Boolean;
var
  Cursor: Word;
  Token: string[12];
  NumberValue: LongInt;
  BaseValue: Integer;
  DigitValue: Integer;
  TokenCursor: Integer;
begin
  DecodeEntity := False;
  Consumed := 0;
  Token := '';
  Cursor := PositionValue + 1;
  while (Cursor <= EndPosition) and (Length(Token) < 12) and
    (Input.Data[Cursor] <> ';') do
  begin
    Token := Token + Input.Data[Cursor];
    Inc(Cursor);
  end;
  if (Cursor > EndPosition) or (Input.Data[Cursor] <> ';') then
    Exit;

  if Token = 'amp' then
    Decoded := '&'
  else if Token = 'lt' then
    Decoded := '<'
  else if Token = 'gt' then
    Decoded := '>'
  else if Token = 'quot' then
    Decoded := '"'
  else if Token = 'apos' then
    Decoded := ''''
  else if (Length(Token) >= 2) and (Token[1] = '#') then
  begin
    TokenCursor := 2;
    BaseValue := 10;
    if (TokenCursor <= Length(Token)) and
      ((Token[TokenCursor] = 'x') or (Token[TokenCursor] = 'X')) then
    begin
      BaseValue := 16;
      Inc(TokenCursor);
    end;
    if TokenCursor > Length(Token) then
      Exit;
    NumberValue := 0;
    while TokenCursor <= Length(Token) do
    begin
      if IsDigitChar(Token[TokenCursor]) then
        DigitValue := Ord(Token[TokenCursor]) - Ord('0')
      else if (BaseValue = 16) and
        (LowerChar(Token[TokenCursor]) >= 'a') and
        (LowerChar(Token[TokenCursor]) <= 'f') then
        DigitValue := Ord(LowerChar(Token[TokenCursor])) - Ord('a') + 10
      else
        Exit;
      if DigitValue >= BaseValue then
        Exit;
      NumberValue := NumberValue * BaseValue + DigitValue;
      if (NumberValue = 0) or (NumberValue > 255) then
        Exit;
      Inc(TokenCursor);
    end;
    Decoded := Chr(NumberValue)
  end
  else
    Exit;

  Consumed := Cursor - PositionValue + 1;
  DecodeEntity := True;
end;

procedure ClearDocument(var DocumentValue: TBrowserDocument);
begin
  FillChar(DocumentValue, SizeOf(DocumentValue), 0);
end;

procedure AppendShort(var Value: string; CharacterValue: Char; LimitValue: Integer);
begin
  if Length(Value) < LimitValue then
    Value := Value + CharacterValue;
end;

procedure AppendDocumentChar(var DocumentValue: TBrowserDocument; Value: Char);
begin
  if DocumentValue.TextLength >= TextCapacity then
  begin
    DocumentValue.Truncated := True;
    Exit;
  end;
  Inc(DocumentValue.TextLength);
  DocumentValue.Text[DocumentValue.TextLength] := Value;
end;

procedure NewLine(var DocumentValue: TBrowserDocument);
begin
  if (DocumentValue.TextLength > 0) and
    (DocumentValue.Text[DocumentValue.TextLength] <> #10) then
    AppendDocumentChar(DocumentValue, #10);
end;

function LastDocumentChar(const DocumentValue: TBrowserDocument): Char;
begin
  if DocumentValue.TextLength = 0 then
    LastDocumentChar := #0
  else
    LastDocumentChar := DocumentValue.Text[DocumentValue.TextLength];
end;

procedure AppendVisibleChar(
  var DocumentValue: TBrowserDocument;
  Value: Char;
  Preformatted: Boolean;
  InTitle: Boolean;
  ActiveLink: Integer
);
var
  LastValue: Char;
begin
  if InTitle then
  begin
    if IsSpaceChar(Value) then
    begin
      if (Length(DocumentValue.Title) > 0) and
        (DocumentValue.Title[Length(DocumentValue.Title)] <> ' ') then
        AppendShort(DocumentValue.Title, ' ', TitleCapacity);
    end
    else
      AppendShort(DocumentValue.Title, Value, TitleCapacity);
    Exit;
  end;

  if (ActiveLink > 0) and (ActiveLink <= LinkCapacity) then
  begin
    if IsSpaceChar(Value) then
    begin
      if (Length(DocumentValue.Links[ActiveLink].Text) > 0) and
        (DocumentValue.Links[ActiveLink].Text[
          Length(DocumentValue.Links[ActiveLink].Text)] <> ' ') then
        AppendShort(DocumentValue.Links[ActiveLink].Text, ' ', LinkTextCapacity);
    end
    else
      AppendShort(DocumentValue.Links[ActiveLink].Text, Value, LinkTextCapacity);
  end;

  if Preformatted then
  begin
    AppendDocumentChar(DocumentValue, Value);
    Exit;
  end;

  if IsSpaceChar(Value) then
  begin
    LastValue := LastDocumentChar(DocumentValue);
    if (LastValue <> #0) and (LastValue <> ' ') and (LastValue <> #10) then
      AppendDocumentChar(DocumentValue, ' ');
  end
  else
    AppendDocumentChar(DocumentValue, Value);
end;

function RenderHtml(
  const Input: TLargeBuffer;
  Offset: Word;
  InputLength: Word;
  var DocumentValue: TBrowserDocument
): TBrowserStatus;
var
  Cursor: Word;
  EndPosition: Word;
  TagEnd: Word;
  TagValue: string[255];
  TagNameValue: string[31];
  AttributeValue: string[255];
  Closing: Boolean;
  InTitle: Boolean;
  Preformatted: Boolean;
  SuppressDepth: Integer;
  SuppressTag: string[31];
  ActiveLink: Integer;
  Decoded: Char;
  Consumed: Word;
  IndexValue: Word;
begin
  ClearDocument(DocumentValue);
  if (Offset = 0) or (Offset > Input.Length + 1) or
    (LongInt(Offset) + InputLength - 1 > Input.Length) then
  begin
    RenderHtml := bsBadArgument;
    Exit;
  end;
  if InputLength = 0 then
  begin
    RenderHtml := bsOk;
    Exit;
  end;

  Cursor := Offset;
  EndPosition := Offset + InputLength - 1;
  InTitle := False;
  Preformatted := False;
  SuppressDepth := 0;
  SuppressTag := '';
  ActiveLink := 0;

  while Cursor <= EndPosition do
  begin
    if Input.Data[Cursor] = '<' then
    begin
      TagEnd := Cursor + 1;
      while (TagEnd <= EndPosition) and (Input.Data[TagEnd] <> '>') do
        Inc(TagEnd);
      if TagEnd > EndPosition then
      begin
        RenderHtml := bsInvalidHtml;
        Exit;
      end;
      if TagEnd - Cursor - 1 > 255 then
      begin
        RenderHtml := bsInvalidHtml;
        Exit;
      end;
      TagValue := '';
      if TagEnd > Cursor + 1 then
        for IndexValue := Cursor + 1 to TagEnd - 1 do
          TagValue := TagValue + Input.Data[IndexValue];

      if ParseTagName(TagValue, Closing, TagNameValue) then
      begin
        if EqI(TagNameValue, 'script') or EqI(TagNameValue, 'style') then
        begin
          if Closing then
          begin
            if (SuppressDepth > 0) and EqI(SuppressTag, TagNameValue) then
            begin
              Dec(SuppressDepth);
              if SuppressDepth = 0 then
                SuppressTag := '';
            end;
          end
          else if SuppressDepth = 0 then
          begin
            SuppressDepth := 1;
            SuppressTag := TagNameValue;
          end
          else if EqI(SuppressTag, TagNameValue) then
            Inc(SuppressDepth);
        end
        else if SuppressDepth = 0 then
        begin
          if EqI(TagNameValue, 'title') then
            InTitle := not Closing
          else if EqI(TagNameValue, 'pre') then
          begin
            if Closing then
              Preformatted := False
            else
              Preformatted := True;
          end
          else if EqI(TagNameValue, 'a') then
          begin
            if Closing then
              ActiveLink := 0
            else if (DocumentValue.LinkCount < LinkCapacity) and
              ExtractAttribute(TagValue, 'href', AttributeValue) then
            begin
              Inc(DocumentValue.LinkCount);
              ActiveLink := DocumentValue.LinkCount;
              if Length(AttributeValue) > PathCapacity then
                DocumentValue.Links[ActiveLink].Href :=
                  Copy(AttributeValue, 1, PathCapacity)
              else
                DocumentValue.Links[ActiveLink].Href := AttributeValue;
              DocumentValue.Links[ActiveLink].Text := '';
            end;
          end;
          if IsBlockTag(TagNameValue) then
            NewLine(DocumentValue);
        end;
      end;
      Cursor := TagEnd + 1;
    end
    else if SuppressDepth > 0 then
      Inc(Cursor)
    else if Input.Data[Cursor] = '&' then
    begin
      if DecodeEntity(Input, Cursor, EndPosition, Decoded, Consumed) then
      begin
        AppendVisibleChar(
          DocumentValue,
          Decoded,
          Preformatted,
          InTitle,
          ActiveLink
        );
        Cursor := Cursor + Consumed;
      end
      else
      begin
        AppendVisibleChar(
          DocumentValue,
          Input.Data[Cursor],
          Preformatted,
          InTitle,
          ActiveLink
        );
        Inc(Cursor);
      end;
    end
    else
    begin
      AppendVisibleChar(
        DocumentValue,
        Input.Data[Cursor],
        Preformatted,
        InTitle,
        ActiveLink
      );
      Inc(Cursor);
    end;
  end;

  while (DocumentValue.TextLength > 0) and
    ((DocumentValue.Text[DocumentValue.TextLength] = ' ') or
     (DocumentValue.Text[DocumentValue.TextLength] = #10)) do
    Dec(DocumentValue.TextLength);
  while (Length(DocumentValue.Title) > 0) and
    (DocumentValue.Title[Length(DocumentValue.Title)] = ' ') do
    Delete(DocumentValue.Title, Length(DocumentValue.Title), 1);
  RenderHtml := bsOk;
end;

function UrlIsLoopback(const Url: TBrowserUrl): Boolean;
begin
  UrlIsLoopback := Url.Loopback;
end;

function StatusName(Status: TBrowserStatus): TStatusString;
begin
  case Status of
    bsOk: StatusName := 'OK';
    bsBadArgument: StatusName := 'BAD_ARGUMENT';
    bsUnsupportedScheme: StatusName := 'UNSUPPORTED_SCHEME';
    bsInvalidUrl: StatusName := 'INVALID_URL';
    bsBufferTooSmall: StatusName := 'BUFFER_TOO_SMALL';
    bsInvalidHttp: StatusName := 'INVALID_HTTP';
    bsInvalidHtml: StatusName := 'INVALID_HTML';
  end;
end;

function RequestStartsWith(const BufferValue: TRequestBuffer; const Value: string): Boolean;
var
  IndexValue: Integer;
begin
  RequestStartsWith := False;
  if Length(Value) > BufferValue.Length then
    Exit;
  for IndexValue := 1 to Length(Value) do
    if BufferValue.Data[IndexValue] <> Value[IndexValue] then
      Exit;
  RequestStartsWith := True;
end;

function RequestContains(const BufferValue: TRequestBuffer; const Value: string): Boolean;
var
  StartValue: Word;
  IndexValue: Integer;
  MatchValue: Boolean;
begin
  RequestContains := False;
  if (Length(Value) = 0) or (Length(Value) > BufferValue.Length) then
    Exit;
  for StartValue := 1 to BufferValue.Length - Length(Value) + 1 do
  begin
    MatchValue := True;
    for IndexValue := 1 to Length(Value) do
      if BufferValue.Data[StartValue + IndexValue - 1] <> Value[IndexValue] then
      begin
        MatchValue := False;
        Break;
      end;
    if MatchValue then
    begin
      RequestContains := True;
      Exit;
    end;
  end;
end;

function DocumentTextContains(const DocumentValue: TBrowserDocument; const Value: string): Boolean;
var
  StartValue: Word;
  IndexValue: Integer;
  MatchValue: Boolean;
begin
  DocumentTextContains := False;
  if (Length(Value) = 0) or (Length(Value) > DocumentValue.TextLength) then
    Exit;
  for StartValue := 1 to DocumentValue.TextLength - Length(Value) + 1 do
  begin
    MatchValue := True;
    for IndexValue := 1 to Length(Value) do
      if DocumentValue.Text[StartValue + IndexValue - 1] <> Value[IndexValue] then
      begin
        MatchValue := False;
        Break;
      end;
    if MatchValue then
    begin
      DocumentTextContains := True;
      Exit;
    end;
  end;
end;

procedure WriteRequest(const BufferValue: TRequestBuffer);
var
  IndexValue: Word;
begin
  for IndexValue := 1 to BufferValue.Length do
    Write(BufferValue.Data[IndexValue]);
end;

procedure WriteDocumentText(const DocumentValue: TBrowserDocument);
var
  IndexValue: Word;
begin
  for IndexValue := 1 to DocumentValue.TextLength do
    Write(DocumentValue.Text[IndexValue]);
end;

end.
