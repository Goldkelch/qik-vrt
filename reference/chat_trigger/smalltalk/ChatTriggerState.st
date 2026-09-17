Object subclass: #ChatTriggerState
    instanceVariableNames: 'repositoryProcessing durableReadback chatTrigger observation continuation freshValidation'
    classVariableNames: ''
    poolDictionaries: ''
    category: 'QIKVRT-Metagrammar'.

ChatTriggerState >> repositoryProcessing: a durableReadback: b chatTrigger: c observation: d continuation: e freshValidation: f
    repositoryProcessing := a.
    durableReadback := b.
    chatTrigger := c.
    observation := d.
    continuation := e.
    freshValidation := f.
    ^ self

ChatTriggerState >> closed
    ^ repositoryProcessing
        and: [durableReadback
        and: [chatTrigger
        and: [observation
        and: [continuation
        and: [freshValidation]]]]]

ChatTriggerState >> status
    ^ self closed ifTrue: ['CLOSED'] ifFalse: ['HOLD_UNVERIFIED']
