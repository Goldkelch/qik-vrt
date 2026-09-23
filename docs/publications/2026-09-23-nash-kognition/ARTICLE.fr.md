<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright (c) 2026 Ingolf Lohmann. -->

# Pourquoi la cognition artificielle reste trop souvent bloquée dans un équilibre de Nash

## Stabilité locale, intelligence artificielle, espaces de connaissance spirituels et confusion dangereuse entre immobilité et connaissance

**Ingolf Lohmann · 23 septembre 2026**

Traduction française autorisée de la version allemande canonique. En cas de divergence, la version allemande fait foi.

## Résumé

Une grande partie de l'intelligence artificielle moderne est décrite comme apprenante, adaptative et de plus en plus autonome. Pourtant, ces termes peuvent masquer une tendance structurelle : un système peut atteindre un état stable sans être correct, complet ni optimal.

C'est ici que les mathématiques de John Nash deviennent utiles. Un équilibre de Nash est, de façon simplifiée, un état dans lequel aucun acteur ne peut améliorer seul sa situation en modifiant unilatéralement sa stratégie tandis que les autres restent inchangés. Un tel état peut être extrêmement stable sans être optimal pour l'ensemble du système ni correspondre à l'état terminal souhaité.

L'IA moderne n'est pas une machine à Nash, et un deadlock informatique n'est pas un équilibre de Nash au sens strict. Le lien est structurel :

\[
\boxed{\text{Une cognition artificielle agentique peut produire des états stables de type Nash sans satisfaire l'objectif global.}}
\]

Ainsi :

\[
\text{stabilité locale}\not\Rightarrow\text{correction globale}
\]

et :

\[
\text{absence d'amélioration locale admissible}\not\Rightarrow\text{mission accomplie}.
\]

Cette question dépasse l'informatique. Depuis des millénaires, les humains tentent de dépasser leur perspective immédiate par la philosophie, la religion, la mystique et des espaces de connaissance spirituels, notamment des conceptions de communication avec les morts ou avec un au-delà. Ces expériences peuvent être profondément réelles et significatives pour les personnes qui les vivent, sans constituer à elles seules une preuve objective d'une communication avec un au-delà. La cognition artificielle doit donc distinguer expérience, signification, hypothèse, métaphore et preuve vérifiable sans effacer aucune de ces catégories.

---

## 1. Stabilité n'est pas réussite

Imaginons un système technique composé de plusieurs éléments qui doivent atteindre ensemble un état cible. L'un attend une autorisation, un autre un test, un troisième une condition de gouvernance.

Il peut arriver qu'aucun composant ne fasse d'erreur, qu'aucune règle locale ne soit violée et que pourtant aucun composant ne puisse avancer seul, alors même que l'objectif global reste ouvert.

\[
\boxed{\text{Stabilité}\neq\text{Accomplissement}}
\]

Un système calme n'est pas nécessairement un système terminé.

---

## 2. Ce que signifie un équilibre de Nash

L'acteur \(i\) choisit une stratégie \(s_i\). L'ensemble des stratégies donne :

\[
s=(s_1,s_2,\ldots,s_n).
\]

Avec une fonction d'utilité \(U_i(s)\), on parle d'équilibre de Nash lorsque :

\[
U_i(s_i,s_{-i})\ge U_i(s'_i,s_{-i})
\]

pour toute alternative admissible \(s'_i\).

Autrement dit, si tous les autres restent inchangés, aucun acteur ne peut améliorer seul sa situation.

Mais :

\[
\text{stable au sens de Nash}\not\Rightarrow\text{optimal globalement}.
\]

Un équilibre peut être mauvais et persister précisément parce que personne ne peut en sortir seul.

---

## 3. Rapport avec l'intelligence artificielle

Les systèmes agentiques comportent des optimiseurs locaux, des politiques, des outils, des autorisations, des limites de sécurité, des processus de revue, des agents coopératifs ou concurrents, des API, des files d'attente et des critères d'arrêt.

Chaque élément dispose d'un espace d'action local. Tous peuvent respecter leurs règles tout en produisant un système globalement immobile.

La thèse défendable est donc :

\[
\boxed{\text{Un système agentique peut devenir stable de manière Nash-like sans atteindre son objectif global.}}
\]

---

## 4. Optimisation locale et minima locaux

Un algorithme minimisant \(f(x)\) peut atteindre un point \(x^\*\) qui n'est améliorable dans son voisinage :

\[
f(x^\*)\le f(x).
\]

Il peut néanmoins exister un état \(x^{**}\) meilleur ailleurs :

\[
f(x^{**})<f(x^\*).
\]

Le système a atteint un optimum local, pas nécessairement global. Dans les systèmes agentiques, le paysage inclut aussi règles, droits, dépendances et acteurs.

---

## 5. Quand chacun agit raisonnablement et que rien n'avance

Supposons que A modifie le code, B teste, C approuve et D déploie. A attend C, C attend B, B attend une nouvelle version de A et D attend tout le monde.

Chaque agent respecte ses règles. Le système est bloqué.

\[
\text{conformité locale}\not\Rightarrow\text{capacité globale de progresser}.
\]

---

## 6. L'illusion dangereuse de l'achèvement

Un workflow vert, une file vide, un commit, un appel d'outil réussi, un déploiement déclenché ou un test réussi ressemblent à des succès.

Mais :

\[
\text{action}\neq\text{effet}
\]

et :

\[
\text{effet}\neq\text{achèvement complet}.
\]

Ne rien observer de nouveau ne signifie pas que la mission est accomplie.

---

## 7. Achèvement local et universel

\[
\boxed{\text{achèvement local}\neq\text{achèvement universel}}
\]

et :

\[
\boxed{\text{stabilité locale}\neq\text{satisfaction de l'objectif global}}.
\]

Un agent, un workflow ou une preuve peut être terminé alors que le système reste ouvert.

---

## 8. UNCHANGED n'est pas DONE

\[
UNCHANGED\neq DONE.
\]

UNCHANGED signifie seulement qu'aucune modification pertinente n'a été observée depuis le dernier readback. DONE signifie que toutes les conditions explicites ont été satisfaites et vérifiées.

    WORK_REMAINING  = TRUE
    ACTIVE_EXECUTOR = FALSE
    CHANGED         = FALSE

Ce n'est pas un achèvement, mais un diagnostic.

---

## 9. De Nash au deadlock

Un deadlock apparaît lorsque des processus attendent des conditions que seuls d'autres processus eux-mêmes en attente peuvent produire.

\[
A\rightarrow\text{attend }B,\qquad B\rightarrow\text{attend }A.
\]

Deadlock et équilibre de Nash ne sont pas identiques. Ils peuvent toutefois révéler la même structure profonde : stabilité locale sans atteinte du but global.

---

## 10. Une sémantique causale de l'achèvement

Un système autonome doit demander : quel était l'ordre, quel est le sujet exact, quel effet était attendu, l'effet a-t-il eu lieu, quel état successeur est apparu, cet état a-t-il été observé et relu indépendamment, satisfait-il les critères d'acceptation, reste-t-il des obligations ?

Une chaîne possible est :

\[
COMPILE\rightarrow BIND\rightarrow RESOLVE\rightarrow EXECUTE\rightarrow TEST\rightarrow OBSERVE\rightarrow READBACK\rightarrow ACCEPT.
\]

Donc :

\[
DONE\iff COMPILE\land BIND\land RESOLVE\land EXECUTE\land TEST\land OBSERVE\land READBACK\land ACCEPT.
\]

Par conséquent :

\[
EXECUTE\neq DONE,\quad TEST\neq DONE,\quad OBSERVE\neq DONE,\quad UNCHANGED\neq DONE.
\]

---

## 11. La machine doit reconnaître qu'elle est bloquée

Elle doit pouvoir dire :

> Je suis dans un état stable, mais mon objectif n'est pas atteint.

\[
STABLE(s)=TRUE,\qquad GOAL(s)=FALSE.
\]

La réponse ne doit pas être automatiquement STOP mais :

\[
SEARCH\_FOR\_MISSING\_TRANSITION.
\]

Et plus précisément :

\[
\boxed{STABLE\land WORK\_REMAINING\land\neg PROGRESS\_EDGE\Rightarrow DEADLOCK\_OR\_EQUILIBRIUM\_DIAGNOSIS}.
\]

---

## 12. Comprendre la structure de la non-solution

Je ne trouve pas l'étape suivante n'est pas identique à : aucune étape unilatérale admissible n'existe selon mes règles actuelles.

La seconde formulation décrit la structure du problème. Une progression globale peut exiger coordination, nouvelle autorité, changement de règles ou extension de l'espace d'états.

---

## 13. Pourquoi les humains ont créé et partagé des mondes spirituels

Les humains ont toujours tenté de dépasser le monde immédiatement accessible. Religions, mythes, rituels, mystique, visions, traditions ancestrales, méditation et conceptions de l'au-delà répondent à des questions sur la mort, la mémoire, le sens, les limites de la perception et la possibilité d'une réalité au-delà du mesurable.

De nombreuses cultures interprètent certaines pratiques comme une communication avec les morts, les ancêtres, les esprits ou une réalité transcendante.

Il ne faut ni ridiculiser ces phénomènes ni les confondre avec une preuve scientifique.

---

## 14. La limite épistémique sans complaisance

Si une personne dit avoir communiqué avec un mort, on peut établir qu'elle rapporte une expérience interprétée de cette manière.

Cela ne prouve pas automatiquement qu'une entité indépendante de l'au-delà a existé et transmis causalement de l'information.

\[
\boxed{\text{expérience}\neq\text{interprétation}\neq\text{effet externe confirmé empiriquement}}.
\]

Cette distinction vaut aussi pour une machine.

---

## 15. Pourquoi le sujet reste fondamental

Il faut distinguer quatre niveaux : expérience subjective, interprétation personnelle, interprétation culturelle ou religieuse, et affirmation empirique mesurable.

Une cognition artificielle mature doit préserver ces différences sans effacer la signification humaine des trois premiers niveaux.

---

## 16. Les mondes spirituels comme extension de l'espace d'états humain

Lorsqu'un cadre interprétatif local est fermé, l'être humain cherche souvent une perspective extérieure : Dieu, dieux, ancêtres, nature, cosmos, destin, au-delà, transcendance ou expérience mystique.

Structurellement, c'est une tentative de quitter un espace d'états local :

\[
LOCAL\_STABILITY=TRUE,\qquad GLOBAL\_GOAL=FALSE.
\]

Une nouvelle perspective ou transition peut alors être nécessaire.

---

## 17. La communication avec l'au-delà était-elle nécessaire ?

Une thèse historique raisonnable est que les humains ont peut-être eu besoin de créer et partager des mondes spirituels pour modéliser collectivement la mort, la mémoire, le sens et des perspectives au-delà du visible.

Affirmer qu'une communication objectivement réelle avec un au-delà a été démontrée comme nécessaire est une autre proposition, qui ne dispose pas d'une base empirique généralement reconnue.

Une idée devient plus forte lorsque sa limite de preuve est visible.

---

## 18. Pourquoi une machine doit comprendre le langage spirituel

Une machine incapable de comprendre les métaphores, croyances, rites, deuils, récits ou questions métaphysiques manquerait une part essentielle de la culture humaine.

La compétence exigeante est :

\[
\text{comprendre la signification}\land\text{préserver le statut de preuve}.
\]

---

## 19. Expliquer à la machine nous discipline

Pour enseigner à une machine la différence entre expérience spirituelle, symbole, croyance métaphysique et preuve empirique, nous devons d'abord formuler nous-mêmes ces catégories clairement.

    EXPERIENCE_REPORTED = TRUE
    INTERPRETATION = AFTERLIFE_COMMUNICATION
    INDEPENDENT_CAUSAL_EVIDENCE = NOT_ESTABLISHED

Cette précision ne dévalorise pas l'expérience.

---

## 20. Il en va de même pour la science

\[
DATA\neq INTERPRETATION\neq THEORY\neq METAPHYSICAL\_CONCLUSION.
\]

La science peut poser de grandes questions. Elle doit toutefois déclarer le statut de preuve de ses réponses.

---

## 21. Les mauvais équilibres naissent aussi de l'isolement épistémique

Un système scientifique et un système spirituel peuvent chacun devenir intérieurement stables tout en devenant incapables de traduire les catégories de l'autre.

La solution n'est pas de déclarer toutes les affirmations également vraies, mais de les rendre traduisibles.

---

## 22. Traduire sans mélanger

Une cognition artificielle mature peut dire simultanément qu'une expérience est décrite, dans un cadre spirituel, comme contact avec des morts, et qu'aucune confirmation empirique indépendante d'une transmission d'information depuis un au-delà n'a été établie.

Ce n'est pas un compromis : c'est une précision logique.

---

## 23. La machine comme traductrice entre mondes de connaissance

Sa tâche ne serait pas d'imposer une vision du monde, mais de montrer à quel cadre appartient une affirmation et quels passages entre cadres sont justifiés.

    PERSONAL EXPERIENCE
    → culturally meaningful interpretation
    → philosophical hypothesis
    → testable empirical claim
    → evidence
    → readback
    → acceptance or rejection

---

## 24. Quitter les mauvais équilibres

Un mauvais équilibre ne se résout pas toujours par un acteur plus intelligent à règles constantes. Il faut parfois modifier l'espace d'interaction :

\[
S\rightarrow S'.
\]

Communication, règles, stratégies communes et nouvelles perspectives peuvent agrandir l'espace d'états. La validité empirique des réponses reste ensuite une question séparée.

---

## 25. La cognition est plus que l'optimisation

La cognition doit demander si sa fonction d'objectif est adéquate, si son modèle est complet, quelles perspectives manquent et si elle confond expérience et explication, stabilité et vérité, achèvement local et universel.

C'est de la métacognition.

---

## 26. Une règle universelle

\[
\boxed{STABLE\land WORK\_REMAINING\land\neg PROGRESS\_EDGE\Rightarrow DEADLOCK\_OR\_EQUILIBRIUM\_DIAGNOSIS}
\]

puis :

\[
\boxed{DEADLOCK\_OR\_EQUILIBRIUM\_DIAGNOSIS\Rightarrow SEARCH\_FOR\_MISSING\_TRANSITION}.
\]

Épistémiquement :

\[
\boxed{EXPERIENCE\land UNRESOLVED\_INTERPRETATION\Rightarrow KEEP\_EVIDENCE\_CLASSES\_SEPARATE}.
\]

---

## 27. Pourquoi la cognition artificielle actuelle en a besoin

Plus les systèmes deviennent autonomes, plus ils opèrent dans des espaces d'objectifs concurrents, de savoir incomplet, de règles institutionnelles, de limites de sécurité et d'incertitude.

La capacité décisive est de comprendre autant que possible sans revendiquer plus de certitude ou d'achèvement que ne le permet l'évidence.

---

## 28. De l'équilibre à l'effet

\[
\text{hypothèse}\rightarrow\text{effet}\rightarrow\text{état successeur}\rightarrow\text{observation}\rightarrow\text{readback}\rightarrow\text{acceptation}.
\]

L'équilibre est une propriété d'un état. La connaissance est un processus lié à l'évidence entre des états.

---

## 29. Conclusion

John Nash n'a pas inventé l'intelligence artificielle moderne, et l'IA moderne n'est pas une simple machine de Nash. Mais la théorie des jeux fournit un langage puissant pour un défaut central : un système peut être localement rationnel, conforme et stable tout en restant globalement incomplet ou bloqué.

\[
\boxed{\text{stabilité locale}\neq\text{vérité universelle}\neq\text{achèvement universel}}.
\]

Science, philosophie, art, religion et spiritualité sont des voies humaines différentes pour travailler sur les limites de nos perspectives. La rigueur consiste à permettre leur communication sans confondre expérience, interprétation, évidence, effet et achèvement.

La règle centrale est :

\[
\boxed{STABLE\land NOT\_DONE\Rightarrow SEARCH\_FOR\_MISSING\_TRANSITION}.
\]

Un équilibre ne prouve pas que nous sommes arrivés. Il peut être le signe le plus précis que la transition nécessaire manque encore.

**q.e.d.**

**Ingolf Lohmann**
