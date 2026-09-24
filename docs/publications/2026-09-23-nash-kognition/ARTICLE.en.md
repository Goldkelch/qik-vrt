<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright (c) 2026 Ingolf Lohmann. -->

# Why Artificial Cognition Too Often Gets Stuck in a Nash Equilibrium

## On local stability, artificial intelligence, spiritual epistemic spaces, and the dangerous confusion of standstill with understanding

**Ingolf Lohmann · 23 September 2026**

Authoritative English translation of the canonical German article. If translations diverge, the German version controls.

## Abstract

Much of modern artificial intelligence is described as learning, adaptive, and increasingly autonomous. Yet these descriptions can obscure a structural tendency: systems may reach states that are stable without being correct, complete, or optimal.

This is where John Nash's mathematics becomes useful. A Nash equilibrium, in simplified terms, is a state in which no single participant can improve its own situation by changing strategy unilaterally while all others remain unchanged. Such a state may be remarkably stable without being jointly optimal or equal to a desired global terminal state.

Modern AI is not a Nash machine, and a technical deadlock is not a Nash equilibrium in the strict game-theoretic sense. The connection is structural:

\[
\boxed{\text{Agentic artificial cognition can produce Nash-like stable states without achieving global goal satisfaction.}}
\]

Thus:

\[
\text{locally stable}\not\Rightarrow\text{globally correct}
\]

and, more precisely:

\[
\text{no locally admissible improvement step}\not\Rightarrow\text{task fulfilled}.
\]

The same issue reaches beyond computer science. For millennia, humans have tried to exceed their immediately available perspective through philosophical, religious, mystical, and spiritual epistemic spaces, including ideas of communication with the dead or an afterlife. Such experiences and convictions can be real, meaningful, and epistemically important to people, but they do not by themselves establish objectively verified communication with an afterlife. This boundary is precisely what makes the topic relevant to artificial cognition: experience, meaning, hypothesis, metaphor, and independently testable evidence must remain distinguishable without dismissing any of those layers.

---

## 1. The basic misunderstanding: stability is not success

Imagine a technical system whose components jointly have to reach a target state. One component waits for approval, another may act only after a test passes, and a third may write only under defined governance conditions.

A state can arise in which nobody makes an obvious mistake, nobody violates its local rule, and no component can sensibly continue alone, while the overall target is still unmet.

From the outside the system looks calm. Internally it may be consistent. The work is nevertheless unfinished.

\[
\boxed{\text{Stability}\neq\text{Fulfilment}}
\]

This distinction is easy to state and surprisingly difficult to enforce.

---

## 2. What a Nash equilibrium means

Actor \(i\) has a strategy \(s_i\). Together the strategies form

\[
s=(s_1,s_2,\ldots,s_n).
\]

Actor \(i\) evaluates the state with utility function \(U_i(s)\). A Nash equilibrium exists when no actor can improve its own outcome by changing strategy unilaterally:

\[
U_i(s_i,s_{-i})\ge U_i(s'_i,s_{-i})
\]

for every admissible alternative \(s'_i\).

In ordinary language: if everyone else stays as they are, no individual participant can improve its own position by making a move alone.

But:

\[
\text{Nash-stable}\not\Rightarrow\text{globally optimal}.
\]

An equilibrium can be bad. It can persist precisely because nobody can leave it alone.

---

## 3. What this has to do with artificial intelligence

Agentic AI systems increasingly consist of local optimizers, policies, tools, approvals, safety boundaries, review processes, cooperating or competing agents, external APIs, queues, state machines, and stopping conditions.

Every component has a locally bounded action space. Therefore each part may act correctly while global progress disappears.

The defensible claim is not that modern AI is Nash mathematics, but:

\[
\boxed{\text{Agentic systems can become Nash-like stable without having achieved their global objective.}}
\]

---

## 4. Local optimization and local minima

Optimization already contains a related problem. An algorithm minimizing \(f(x)\) may reach \(x^\*\), where no improvement is visible nearby:

\[
f(x^\*)\le f(x).
\]

A better distant state \(x^{**}\) may still exist:

\[
f(x^{**})<f(x^\*).
\]

The system has arrived locally, not globally. In agent systems the landscape also contains rules, permissions, dependencies, safety constraints, and other actors. A local minimum becomes an algorithmic or institutional equilibrium.

---

## 5. When everyone acts reasonably and nothing happens

Suppose agent A may modify code, B may test, C may approve, and D may deploy. A waits for C, C waits for a test from B, B waits for a new version from A, and D waits for all three.

Every agent behaves locally correctly. The system stops.

\[
\text{local rule compliance}\not\Rightarrow\text{global ability to progress}.
\]

---

## 6. The dangerous illusion of completion

Technical systems produce many signals that look like success: a green workflow, an empty queue, done, a commit, a successful tool call, a deployment request, or a passing test.

But:

\[
\text{action}\neq\text{effect}
\]

and:

\[
\text{effect}\neq\text{complete closure}.
\]

No new change observed does not imply task fulfilled.

---

## 7. Local and universal completion

Artificial cognition should therefore understand:

\[
\boxed{\text{local completion}\neq\text{universal completion}}
\]

and:

\[
\boxed{\text{local stability}\neq\text{global goal satisfaction}}.
\]

An individual agent, workflow, or proof may be finished while the system remains open.

---

## 8. UNCHANGED is not DONE

\[
UNCHANGED\neq DONE.
\]

UNCHANGED only says that no relevant state change has been observed since the previous readback. DONE says that the explicit conditions of the task have been completely and verifiably satisfied.

For example:

    WORK_REMAINING  = TRUE
    ACTIVE_EXECUTOR = FALSE
    CHANGED         = FALSE

This is not completion. It is a diagnosis.

---

## 9. From Nash to deadlock

A deadlock occurs when processes wait for conditions that can only be produced by other waiting processes:

\[
A\rightarrow\text{waits for }B,\qquad B\rightarrow\text{waits for }A.
\]

Deadlock and Nash equilibrium are not mathematically identical. Deadlock comes from computer science and synchronization; Nash equilibrium is a game-theoretic stability concept.

Yet both can expose a deeper structure: a system may be locally stable although its global target has not been reached. Stability alone is therefore never a sufficient completion criterion.

---

## 10. Artificial cognition needs causal completion semantics

An autonomous system must ask more than whether an action ran:

1. What was the task?
2. What is the exact subject?
3. What effect was intended?
4. Was that effect actually executed?
5. What successor state actually resulted?
6. Was it independently observed?
7. Was it freshly read back?
8. Does it satisfy the acceptance criteria?
9. Do open obligations remain?
10. Is the state merely stable or genuinely complete?

One possible runtime semantics is:

\[
COMPILE\rightarrow BIND\rightarrow RESOLVE\rightarrow EXECUTE\rightarrow TEST\rightarrow OBSERVE\rightarrow READBACK\rightarrow ACCEPT.
\]

Then:

\[
DONE\iff COMPILE\land BIND\land RESOLVE\land EXECUTE\land TEST\land OBSERVE\land READBACK\land ACCEPT.
\]

Therefore:

\[
EXECUTE\neq DONE,\quad TEST\neq DONE,\quad OBSERVE\neq DONE,\quad UNCHANGED\neq DONE.
\]

---

## 11. The machine must be able to recognize that it is stuck

A more mature artificial cognition must be able to state:

> I am in a stable state, but my goal has not been fulfilled.

Formally:

\[
STABLE(s)=TRUE,\qquad GOAL(s)=FALSE.
\]

This must not imply STOP. It should first imply:

\[
SEARCH\_FOR\_MISSING\_TRANSITION.
\]

More precisely:

\[
\boxed{STABLE\land WORK\_REMAINING\land\neg PROGRESS\_EDGE\Rightarrow DEADLOCK\_OR\_EQUILIBRIUM\_DIAGNOSIS}
\]

A stable state with open work is not automatically a deadlock. The crucial question is whether an admissible progress edge exists or can be reached.

---

## 12. The structure of not solving

Artificial cognition should not merely find solutions. It should understand why it is currently failing to materialize one.

I cannot find a next step differs from: under my current rules there is no admissible unilateral progress step.

The latter describes the structure of the problem. Global progress may require coordination, new authority, an expanded state space, or a rule change.

---

## 13. Why humans created, shared, and transmitted spiritual worlds

Humans have long attempted to exceed their immediate experiential world. Religions, myths, rituals, mysticism, visions, ancestor traditions, meditation, and concepts of an afterlife are diverse responses to questions such as:

- What lies beyond immediate perception?
- Can knowledge arise outside my local standpoint?
- What does death mean?
- What remains of a person?
- Can the living and the dead remain connected in some sense?
- Is there reality beyond what is currently measurable?

Many cultures contain practices understood as communication with the dead, ancestors, spirits, or an otherworldly reality.

This should neither be ridiculed nor confused with scientific proof. Either mistake would be epistemically careless.

---

## 14. The uncompromising epistemic boundary

If somebody says, I communicated with a dead person, one fact can initially be established: the person reports an experience interpreted as communication with a dead person.

What is not automatically established is that an independent otherworldly entity existed and causally transferred information. That claim requires additional evidence.

The scientifically disciplined position is neither That is impossible nor The afterlife is therefore proven, but:

\[
\boxed{\text{experience}\neq\text{interpretation}\neq\text{empirically confirmed external effect}}.
\]

Artificial cognition needs exactly the same distinction.

---

## 15. Why the subject is nevertheless fundamental

Spiritual claims are a demanding test case because people speak on different logical levels:

1. subjective experience: I felt the presence of a dead person.
2. personal interpretation: I believe that person communicated with me.
3. cultural or religious interpretation: My tradition understands this as communication with ancestors.
4. empirical claim: Objectively measurable information was transmitted from a dead person to a living one.

These statements are not logically identical. Good artificial cognition must keep them separate without erasing the human significance of the first three.

---

## 16. Spiritual worlds as an expansion of the human state space

When humans become trapped inside a closed interpretive space, they often seek a standpoint beyond it. Historically that standpoint may be called God, gods, ancestors, nature, cosmos, fate, afterlife, transcendence, or mystical experience.

Without deciding the metaphysical truth question, this can be read structurally: humans attempt to leave their local state space.

That resembles an algorithmic system for which

\[
LOCAL\_STABILITY=TRUE
\]

while

\[
GLOBAL\_GOAL=FALSE.
\]

A perspective or transition unavailable inside the current local optimization space may then be required.

---

## 17. Was communication with the afterlife necessary?

A historical or personal thesis can reasonably state that humans may have needed to create and share spiritual worlds in order to model death, memory, meaning, experience, and perspectives beyond the immediately visible.

A different claim would be that objectively real communication with an afterlife was demonstrably necessary. There is no generally accepted empirical basis for that conclusion.

Artificial cognition must not blur this distinction.

**An idea does not become stronger when its evidential boundary is hidden. It becomes stronger when observation, interpretation, and metaphysics are explicitly distinguished.**

---

## 18. Why a machine must understand spiritual language

Artificial cognition that can understand only natural-scientific protocol sentences would fail to understand a large part of human culture. Humans communicate through facts, stories, metaphors, symbols, beliefs, rituals, memory, hope, grief, and metaphysical questions.

Understanding spiritual language must mean neither treating every metaphysical statement as physical fact nor dismissing spirituality as meaningless.

The harder capability is:

\[
\text{understand meaning}\land\text{preserve evidence status}.
\]

---

## 19. Explaining it to a machine disciplines us

If we want a machine to distinguish spiritual experience, symbolic meaning, metaphysical belief, and empirical evidence, we must formulate these categories precisely ourselves.

For example:

    EXPERIENCE_REPORTED = TRUE
    INTERPRETATION = AFTERLIFE_COMMUNICATION
    INDEPENDENT_CAUSAL_EVIDENCE = NOT_ESTABLISHED

Nothing is demeaned by this. The statement simply becomes precise.

---

## 20. The same applies to science

An experiment generates data. Data are interpreted. Interpretation enters a model. Further claims emerge from the model.

The layers must remain distinct:

\[
DATA\neq INTERPRETATION\neq THEORY\neq METAPHYSICAL\_CONCLUSION.
\]

The boundary between science and worldview is not that science may ask only small questions. It is that science must disclose the evidential status of its answers.

---

## 21. Bad equilibria also arise through epistemic isolation

Another Nash-like condition appears when worldviews react only to their own premises. The scientific system accepts only its own evidence forms; the spiritual system accepts only its own experiential forms; neither can translate the other's perspective.

Each becomes internally stable while the common epistemic space shrinks.

The alternative is not to declare every proposition equally true. It is to make propositions translatable.

---

## 22. Translation instead of conflation

A mature artificial cognition could say at the same time:

> Within a spiritual interpretive framework, this experience is described as contact with the dead.

and:

> Independent empirical confirmation of information transmission from an afterlife has not thereby been established.

Both statements can be true at once. This is logical precision, not compromise.

---

## 23. The machine as translator between epistemic worlds

Artificial cognition need not decide a worldview for everyone. It can instead show which claims belong to which epistemic framework and which transitions between them are justified.

    PERSONAL EXPERIENCE
    → culturally meaningful interpretation
    → philosophical hypothesis
    → testable empirical claim
    → evidence
    → readback
    → acceptance or rejection

This is more capable than either blind affirmation or reflexive denial.

---

## 24. Leaving bad equilibria

A bad Nash equilibrium is often not overcome by one actor becoming smarter within unchanged rules. Sometimes the interaction space itself must change.

New communication, rules, joint strategies, and perspectives can arise:

\[
S\rightarrow S'
\]

where \(S'\) may represent not just another state but an expanded state space.

Spiritual, philosophical, and scientific shifts can thereby enable questions that were not formulable before. Whether the resulting answers are empirically confirmed remains a separate question.

---

## 25. Cognition is more than optimization

Optimization asks: Which admissible step improves my objective function?

Cognition must additionally ask:

- Is my objective function appropriate?
- Is my model complete?
- Which perspectives are missing?
- Am I confusing an experience with its explanation?
- Am I confusing stability with truth?
- Am I confusing local with universal completion?
- Is my standstill itself evidence that I must expand the state space?

That is metacognition.

---

## 26. A universal rule

For artificial and human systems:

\[
\boxed{STABLE\land WORK\_REMAINING\land\neg PROGRESS\_EDGE\Rightarrow DEADLOCK\_OR\_EQUILIBRIUM\_DIAGNOSIS}
\]

and therefore:

\[
\boxed{DEADLOCK\_OR\_EQUILIBRIUM\_DIAGNOSIS\Rightarrow SEARCH\_FOR\_MISSING\_TRANSITION}.
\]

Epistemically:

\[
\boxed{EXPERIENCE\land UNRESOLVED\_INTERPRETATION\Rightarrow KEEP\_EVIDENCE\_CLASSES\_SEPARATE}.
\]

Standstill is not proof of success. Uncertainty is not proof of the opposite. Both require further epistemic work.

---

## 27. Why today's artificial cognition urgently needs this principle

As AI systems become more autonomous, they increasingly operate amid competing objectives, incomplete knowledge, different worldviews, institutional rules, safety boundaries, technical dependencies, and uncertainty.

The crucial capability is:

> Understand as much as possible without claiming more certainty or completion than the evidence permits.

That matters for technical systems just as it matters for questions about consciousness, death, spirituality, or a possible afterlife.

---

## 28. The decisive extension: from equilibrium to effect

The goal of artificial cognition should not merely be to find a stable state. It should be:

\[
\text{hypothesis}\rightarrow\text{effect}\rightarrow\text{successor state}\rightarrow\text{observation}\rightarrow\text{readback}\rightarrow\text{acceptance}.
\]

Equilibrium is a property of a state. Knowledge is an evidence-bound process between states. Completion is justified only when the declared target space has actually been reached.

---

## 29. Conclusion

John Nash did not invent modern artificial intelligence, and modern AI is not merely a Nash machine. Yet game theory provides useful language for a central failure mode of contemporary artificial cognition:

> A system may be locally rational, rule-compliant, and perfectly stable while remaining globally incomplete or blocked.

The error is not equilibrium itself. The error begins when a system mistakes a local equilibrium for universal completion.

\[
\boxed{\text{local stability}\neq\text{universal truth}\neq\text{universal completion}}.
\]

Humans also live inside limited perspectives and attempt to exceed them. Science, philosophy, art, religion, and spirituality are different human ways of working on those limits. Ideas of an afterlife and experiences interpreted as communication with the dead belong to this human epistemic space.

The intellectually disciplined position is neither to ridicule such experiences nor to convert their significance automatically into scientific proof. It is to keep the levels distinct while still allowing them to communicate.

Artificial cognition could help. If we can explain to a machine what we experienced, how we interpret it, what we believe, what can be tested, which evidence is missing, which transitions were actually observed, and what remains open, we can probably explain these things more clearly to one another as well.

Perhaps a central task of artificial cognition is therefore **not to reduce all human epistemic worlds to one, but to understand their differences precisely enough that communication becomes possible without confusing experience, interpretation, evidence, effect, and completion.**

The central rule is:

\[
\boxed{STABLE\land NOT\_DONE\Rightarrow SEARCH\_FOR\_MISSING\_TRANSITION}.
\]

An equilibrium is not proof that one has arrived. It may instead be the clearest evidence that the next necessary transition is still missing.

**q.e.d.**

**Ingolf Lohmann**
