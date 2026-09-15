"SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0"
"The first pipe record binds this process; subsequent records are live events.
StdioStream next blocks for input. No Delay, clock, HTTP, or polling loop."
| input output reactor line config response |
input := Stdio stdin.
output := Stdio stdout.
reactor := nil.
[ input atEnd ] whileFalse: [
    line := (input upTo: 10) utf8Decoded.
    line ifNotNil: [
        response := [
            config := STONJSON fromString: line.
            reactor ifNil: [
                reactor := QikvrtEventReactor new
                    bindRepository: (config at: 'repository') subject: (config at: 'subject').
                Dictionary newFrom: { 'status' -> 'READY' }
            ] ifNotNil: [ reactor accept: config ]
        ] on: Error do: [ :error |
            Dictionary newFrom: { 'status' -> 'HOLD'. 'reason' -> error messageText.
                'completions' -> #() } ].
        output nextPutAll: (STONJSON toString: response) utf8Encoded; nextPut: 10; flush ] ].
Smalltalk snapshot: false andQuit: true.
