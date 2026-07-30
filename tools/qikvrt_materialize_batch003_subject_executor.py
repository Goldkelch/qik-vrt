#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Temporary deterministic bootstrap for the reviewed Batch-003 subject executor.

The bootstrap is transport-only. It writes the byte-exact, human-readable Python
source and is removed after repository evidence materialization has persisted the
source file on the candidate branch.
"""
from __future__ import annotations

import base64
import hashlib
import pathlib
import zlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET = ROOT / "tools/qikvrt_content_disposition_batch_003_subject_2581811b342e505d.py"
EXPECTED_SHA256 = "7f342dff408d3800fa057cc372a1be6b45a4531ef4ad06319eea9513b556a8a8"
PAYLOAD = """c-qZ<*>c<1lHfbP0v8n>MY_0(TG^wHpd`A?E?II*blvjRRlpztO1P#-7695-
sns!06Z1Mt^wYe|Ps|71FPU7<iiM(VS9dw0N(7K+%abQhZYR%oe`>9gxHXREt#JO)S>C6&i+Q*5opbr-<d?>2GzsTP*cb-kJdLJN
826n1(x2Rhjjd)IppF;I`#8F}O`Waw)~++0-z;WR=X7y<=g;TOitD-
;;bieKjOz~kFPh#v{ycEfFusfC{%m&d1W~eFBvBeI=FX9yPHr3RcGpQ(<G+OysB~w)v)}2AyW3mgPJ1V4Rw|?0&`CcnoaJgfizd!
r!ucXtILTraPeNxJ&BDa-
<Isuj?pCQkp24sAa+M}c$H9`fQIam=XyVUA1(i6QgwZkuups>GM2Uj{Vc@LbId*&}2m=65;SCpPOye;8Ep(QCdP{@3TP3M84`F!D
IIKX=lQc?KSm09xAStx!FPGswXe{P1;92xBbgV|HYtV4`Ih?GZamG{x1A(&GzeOBC37;#d16&&WlN1U7;5|Gpp<7YvOlE#`=Ro;+
c;lzo48IvKU@U%oU$5N3IO52kMZaO?ixjZHh-;*a1_NW&p+AmhQ3_4r`266bKc7GW>VAqn71KlWTbag-JIC{;t8^8Io(Gs;F5(o5
&Y=OE*Q8RB@8X-KA19%Fo&fd8-
?x5pJB!Bh@o&juE`KAcjZevaB7dgQovLgV&j6?y#_=M~yt5h=@8a;+RhXpQ{mEiBg8^Y@W&e)>Yk)2Op58B``HlS4p95-
+fqap^>dp|r_}6QgXn?CbmsmL<tx~x-
KOZ@VatO^g@V5%c0y_1)8gwFA%sz(I8g>zuSaQ|5t{n9*2j0ct6pB?V4*YZDa2EPW*!qo#y#WNVTqTWVyjV;dxb7P5y~fslYvRur
bENIYY7Rqbxm<d(fPu`@hOyKdW4Y8?VlK_EN$c|M(LWE4M~&?Ib1OCK9(0Wc)^cQLD{tN&oeqz^mluP<U+_DDwH()4HLe7^7#t6V
Z${o(|1|=;{tEa`3^doci*N!PfIuH<P>*j92Ha`y!vA-6n@Aq2vf<gu;1^YuDk&CO(%@BQ6%p+Nyxs4XQ_w-Ho$?~O8x<&h{`27C
ozafOhgI0i0*YQ9pZ15Zz1RKG#qbxStod3%jxPGggZ|O*bU1ovKwh4|y*M6tqjQhTm|&u0|MGHhF&dtqdDMmekLIlDk7ws60|g<w
cYZb+oQ=Gb!SV1CfXpt6PsgwNXFm=UgeWNJssJtW%gONa&H3e!nznIrHuz=a{rUXjC-
3dqaHJLo(jonTN<J;(4@moI;>uT02!=lL`WMHqhCky-xPPNpgEOl!!qcU9)E^zc@?c?jvPYf0t&@|3qvNf;?*7aEc2{(#R(W<`#A
JJeU$93O)f~MW4KBU@*@-7R4E?#h9KL*4&?B)bk6={}U{#)|9-ZO{C6$T=>V_Yq0C`bMu7_5BJ@g3$gP(^dgR^5}bt}%Z$@-
M+iB~+ae$fbF>P`RnCnmByvVKnnhi~yga=LQvChOxRBPIe7WA<MmTM_f{1ldkG%Ot`r1_s&+f`jn{X>00lcijrlHbV(oZ5U+Qpzk
;?mzd1O3Bzu6cDvo}PN#BmKE$G(c5`QIzatRZl%Hwo9uI)8t%Ym5mGdKD06z~-ygrh*D<`4b9<|%Oo&DZU`!8Z-
gO@L1D0;Jc?urvge|q5|(nsg#r($n()5T(zw0?~~e2i01(12&qfJZbyRf?(ia`NQz9#HaXaQqW=^Yv?3e^Bw%6;iO%IC36ji;qsD
0dnu;gIlQ#et82O1my7Qfie#?h=RSNCqB^_$M<QNxIJg5vwu+6ukV5#c<Ju%9c*>?cfxkNz0=;B`r&SO>UYN5;r4#Gy|>kMjUvgd
zqPZArM9|z2-`i_J~)_$<M9|u2YY*+$#`oL?rx2PaPMGu&)++k1i?<&9d~vP{O-
;{XFAz$`;&uxv(}p^^~STs*n{dj)TJ&!O?J9Lx7!ZK2U`b0I30KQx(DH8a?sh|4tMu<ws*S+qLRnDi3YtN79yduy}y@7g73GxT|e
|E<Gt<ea2o7S#`_2UWPdsdc6ax>B}mxbo4}wu?Y;KF{-nLLwTFZA+rjQm5QgD+*YE61!p`==?#}-
HH1NCdUweNq*bX}T!OnELy%q^u+hNciPuqLl-SPJJcCgcdVefS(ySw9^y>1&Yy*obG+uGAec&q>`J|3Krp!6V^)XYy35bK#SV!d~
uM@93{L(v}PNBEJ(i)4v{=*Q3_dEBIDQNKHpIu};5RsoYGW~{~${Bh&xUE}Pyady(!Znh-
^RgrkNiy3G=2$!n}##Es(IG4PbPIS)(xFu9CKwt)WoE~aDs&@(SP!6cZnflSJdKV^%e-
rjV$%<=E<DZ<f#XMxt*pHI1v~E$bCMsJ3s?z)FM}M}0%0M2c%AitFR|vYuoOFn0u)13&3<;{!JV7PJPbN`x_|l&x@D6vwd3v~2bA
E8#zXEILCYZQ9qSk8Qr+&|&--Rs+<)z7m2)x$34L=9b4d@tE*=?ZlXI2O$2)6F5k}#MqK#!TMa3AL07d2whZ+S!0*uMiE71<p^I}
fvP&K-
aJYujyt#IOj$s!OPH5jXg)WXzo^*H+XWR{Op1GpMX$@N<AA5~w@b?rC}ewH640dYECi&6_Z#I%)(MO*Jg&rn&|iB~sngUCkAUup6
KT25bqdd33p=#W)G$kJMrTyHe=M@hp2*YeftyM@+Rf3@1N<0{T&oSM~HyhidG(F%!n+aIt0QE=uljOLTya#Lxi+vNA-
2SY4<tiy6Z;v~I$L%6mm0VIf{~KT2ku%QL#u_+Iy!)+ZpImh5cd2aKj>5HcCA(rIJgt<?l+Ou}XARNsOu2wzVKhWJFCEBNQj^E2a
Z&GFH?GSSVgXEswennQ=8z_D<MwQ96MeSk5C%meUSPR)Fg0u@H{Bt@f%<U0aOwcI3$s)hLq$QR4|bC_Z5S%yHx!lOFHR3WNB_PM)
@QlJ5ktMgdduF?br(In;Bp=prwgLNdm+*hQ1CNrcFo-
(p@MRTWGEs$^O8KI|EcdEJlzix>HH3JP65#T?Zbzv`Q;>IY5r>20!<iCXVd$velqHT+2EjPzc&$9(eV|HPQBxvc0*=lL<3qmPOi0
IjjENou7sG=TIdvvYJGIX)wiqI2tg`aRT6w?LL(%M}!O2~u+GmI8Gi@O+5CjM&9VUCer<tFO-
O7g7h45_+gw=@lzw&C;>pg)2=BZk*0eO=D{3E*#hPbScu;Z<O?fV8E=AS`rZ1O&E<XUvD_=>`AsCrA;-
`#b+L7wSQmQUL_(;|`QxdIgBx=GO}t4;r<lHSg-mHV-
y0_;1~r!ct4Gna4T*O4|%ngMaE3T4>xN)e2$~^k+bniiT|qT(#=~GG_3S`+$bq>de0z2fiG6o$Q;771WjK6+B|8Y8LQN{1uE6*RU
8kF5uXo--K0(31bzCYM?L0qqkQIz|^f5w?JoMoE$#n7L?nkxq(fMC#jx?cniBvqkjV;7>b>&&9U|lid#ckCv&QLN6D`8-
=lu4mGc*}$t&z@1a`LC%{FZmaR_Vzq~%_oJ)qCRgW&_BBoqoG@Wx<J@*nM@fyOC4<IE+?S(H{)W%-h~3z~~6*U-
dA<OfJ0u3Llc@lzNVG#H7UJ7^}Lr~*7l2kvc}E)$o$0<g2>S)OhWfQ1!c5#LY=d=G+PkRZ~kZqxXjZ@tzltXu4J!c7AVH9`jAgvr
ET0(O9*#0!*Ug2kO5&4IrvygU{(B6bIbeB^LdwcJ5S?G&O#$!^X+8O&i_e`O1_-
Gl*j@Ie)PWNC`rD$wDQt_qH(7`Q38n68TE+lx~nyNr18il_6-
65&O180XO1V8mGEdIwxM|3$OCT>p?$G?Q5vE~{HFUI@5aWfSRWH7Cbfx*)F<V*n6=ebPcC`>kl3N~-+O%S(&IIcKmpTxm%J-
(O3m@DoipmL{>^rTPTAr4Un89*SLE%bn8@$e_kL6{ux|&jd?gCDjN}Q6t`oznF1;%2b12v{=Utg|mXD@{%8Lx;Ucd0DuQ2UV%87t
04oRD}?4?k^rJ&OukW86e;R~+!{WF_jMt8!yrY0CJqe*hF;M^+C;LoiXZ|HNy_8`wNkKV5~e^m{%Qu}g`T-
}>|ZfFPgs+s5uUG7DPkI;5l{%mOi5K!dJsE+Ap$g;O+y^Eq!6*y7t7TCG7_7^l-
X{t)zU1p1)p2oe$skSwp$@M!aR!3=_ae9!n)Wz4_z3rw5+$t3|-
gk>~P<C;dI(t+u~1wlBF6jv@G55f3~irwg~DZR=cs5#bu1Ofopf3R!znc1ungZO&<0|h5xLWYxg3exQFy!sm>Wwffp>I41<C<+>r
Tl83hSU*27~>0~wEz3a@Z$SskC6pz+R~2NE}(lk?$YPLmWJN4tIinnr49_E-fmW}1%0r$lwxV$a<4_}*i6UlVzbYiHC%sFJuO)U3
Nj63ZdJ<T2usX1vHZ*fv6CUh}IGuEr`8S`Tf8BYLg$Ca6s!68K70e5R?#=Zqqh)yu7_C1wr7Q3L9bShf{EG`k2x(?ha|;cu?3$GW
!PNEq2aLyeTv6(+zDH&N7a3QC$Z7UKdpR0~^%bW&z<%K#?PZ`Rb}vpr)3A*>ms`k<PMD-u7{OtaOMFtA-
`wkM0I@50n4(GOu86O7DIL~a^L@E`eTlGUBrLHVwftRz4YX&DvDpCEVMfz-
N;!)f%nie|uGMgoNDRXJ<4XfnJmP%Vnb`}$<3bfB|n{vk0(NiXs;MCNl=f)G?B6g#Mo-~`^-
sm2S`cpof2&2jt4eMrLD)JAfKQ`2^q$MLVLMVi-@=&fAx{xm#vGgyB9ZrdV;*LvUvA6s&Sm7IpLiQ-
$dFE3!8(*_JN^nsjSv|jw<uZQhsC!?(DZM(B;@7qOM?1r`@<`sF{kr0dcvu&2Q<RZ_%@o}aMgJQ8IQQLVHBofYATcqg89pD}3tUx
NOJ)fOLQ&FWDG%PjM0e-cPt&kcQhs=#>_F#<DX&5JthzgT~%NhX-tg?p7KwuLjj-
D1Y41+)J{yp5Ojdv6gMw|^kZPm@naD17GibD}2h)s-Q5X5x>`Gr_KdM*SOxgzCC5MC}aJVSj`)5yPEL>T*~-
E>*^)YN4ZeD@$gAEn!jy_Udqc<JzC6d2Yy-
~=GB!=lSu@<eagH=_&iThS8edosEXiSe3Y!X>D5;T>Rze3Y5yR^|&Cd}_K@jn6V#GT#C1ZL|%4Me8C@6tZ5J5FL=IzDhj7SNYTUn
i(AcW!@OD6f}bqieOjQ<`*58<IVi}&C0(CJw^|ChR<KW>5qm-rvvZL!_g}<RKs$*>p3FYQcrmpIb$xX=+(^YTE2wrwn3I=3z9HdI
~NbkD6E>V^EK1t=?=5@YCuV%L=gEq^PSMdKa4L$<OFa<ukEEbUPZHjz5FDBqcOd}Lc$K}&(F7=aLrFyN9L=$G2rmf>9D+sJ@bR0n
pvgJix(e0`SDGnz3sN6b-n<J0ImC6p%%xe7gAN%++pe-
buYJe_8Sjepx5pOk8a&SzG||jcR118A5?c`@Uy4NCARxk1+IA<xaP^gHP7InZeK#RUK5lfp-_mGfJAiY%Mg?Gec~jO1zIs-
%>i%4csFyUgs_#se(g^_fC4tB=nIaO^7_X=c_-
&*1FRjS3?J5Ia%(hzt|#;j#37N+BEILAtm@fNx@3Ofz8s$QPrWz&%ge8;bTymZdmqAh9?leoJW&)k_vI{<@hdM8)?wI&LXvDo!)7
{UwI{p()g9-
V@YGCrlUtBwWRD5?82_K0Fo(dHBTHA6a%?4X5UQz1i|AO5Mpz*(6Rm3%J|p|eVz!+kT|o=#8|g;&D}%JNdaA2>BKyoi{7OA_wM<3
EK2;SN{PGRtjepWHFM+S1p6fLNzAy`p7mHb~Q1&Y6vQQR}pj_yq9{}1hwH@Z6AF(UKVwsTOqX3X;S?v|D@r;adSme(x0+##A;nmb
_@hrEvgV#2EW?MdV2e01@FNVkc)6;h<y!ON;SB)GHX<;&8`{?}b*-
1uM;4SCSy?p!T&H2Tsxcu4q$QxXa`Y@o&SA%R7MZ1yFIn_1Meo_5{A3-?ySwQqJ-ep>lGR<M$#pM1>_C0bM%Qek`6=F5!xUXKGa|
%)#i*qN26Im`ix6lnH`kwp7W9b7e;txegzFrKtku?n7rDQc3nQ{JRaHf$%(w4ITmUY7c&zU%YLUN*Z4>KZ&viE>Gl4UHGj#A2B2&
y#J#FgvKR(Lqj#1U~1S$?6M15_x_9iS5cN4`U4Z1h2fvJEJpV@GpiseS?1usgjO%gAwrDQyA8co4P%s-!7`7pmWT-
`Ab*o$qUpXw`lIK}dKpq!0G7>3(DGV)g2)n9L?jgy)x61;%M#^iPJUX@4F2DB%n)opO_Luzb8t;5`h?-
QB>zKRQvW!lKA$ISUgixd45(1pDjO7wrn!^+hlBx?-
3=8E1*KC<IHx%gP#V*;3<*%$?YxNjGyM(JqG4&_>OhSlF2Ua<u2R7z=d=eqjsrOLPe}Q-ca~6j-
u*<%v#zE2gQEicA^`1%Alrrj8{pOwkRx%Yjii4u?Zo(f&*@2^p8v@lZrn0S1|ds3ra;=m(GWOlONvSrU@(J$c-
wlub*>a!#$<kad-F=>z~MHqTIW*i48)IXHz<?a?o7cK~iSvOyXOR=LiEi)DlhovgnYh6Jxja@{Fp-udwu{*wo6&t%)=cn?0;rCTW
kr4JN<lv~bh4~5-
Z=anw)61PUKNZF~@1N0*s+X1`TWVT9h&oDg<>TL!*>juksx1_H?S1Mh7ZnBz8fY;$1CLbcup9A+%#_??65nDT0qdjXH3P&t?1R4z
rLMB@|(r=lSwP?ikFDMwV=E!%xq^L0+cJXUFJT&wZdmi~seu4y~;nK=uTjEI?J2n_$QENG|g@;T9izE{@yWg`-
_IokA6ttuf@tBvCe{i6W91$nR_rQNatT6`7;z84`<!9nq;!e@FBY)%}zevh?YSZ~90!@BHVtEuLm^fvzhV>R>Z&$MfR83n}(=Ejg
?>!GDQ|TE?78nApsh)_>cEv*J8Dz|FYL9jsVh@|6d4#ms>@KFilx|-
dB(n+V5408Rl?g?pU|ER?3hfoN1*GBU)ZPP(R(fkTDJ;lbQL;>YQ@A_H_>+9UfGcL$;S(x_R3b62#Uf;0!BswB^WR=u(AW^1`zcj
n12e<mmp9On;Ru!)8Wrf2=7t)<`P-3q{?fZV1|@mD7Jy2(szfKOV1Z4-
lJKt(Nr9p`o7g1%W<!Etb?{1dWUX32l#$cASq|cZ(HwCnMQ?d(x?JsEBM)^7Hf;QO)xItl|MH>o9AdB3gUo8-
m=00x(^`h8Gn*zsG=j=HI)T|j1B8sx8;ZW?X?*{Lx?!C9Sf^~{@%u;7FUaf*6BW-
@$`eyxu%?6^!fYEtuo)&;$)|f^x++sLI#R(Xo;oT_3i9uv9e(L_wc0{o{G+Lbk@Ct2b3W^Pyn<kVESm)#&BVrl4JO4I!=J?R86av
=8I4l0f}G1&{l?bLF6pB`0zad}mLjeY!)<@J>7j@MaheBJ`63wm=wTTY9(h_j&rgYF&!6xOL@|5vaVjW9kKwNq;Vg#1Id`l}&Km{
Ql+wn7Ya+8}hcL?5wR-+2rvkJ;NV#ki>QcsW2M<UP8NIo1zU#Dik<Ns{-1@Y$`z?sdj)5$s3uSU>Vf&d)_o*Vw)okX8Fso-
4)uzIY3bF-c^F9jrXLnGPE9~7LXmewKhl*?#3rF}ja7RmSvp#~UGg-x$pUSk-
B0kqG88u(#I?yj`$~I+w7jHIOAY`(Uq0>qBn4w(S6ndJj_tk$}&TAM=%UCK~SpPVCry_?)?pug9jm<UlY>d{_K=oUkX&$ffonLG?
&%!r@6Rc7I$urY(nwS1P1|Z7)_IDI}WNZ=-
P_!#|fj^Kq#Q2eT!E_BcyVBvp3m%{DmXxiK6WztDIcGaeV}G8AEPZzz9PqU0v=%j%NQF4QiJ8Axir1Y#kEVFw#(*f*y$qO*^eLt%
*@V>z+qS+|gW_6(5T-RIzT>CP4W8j8#91to8%mr{AaqdYQH?+-
J_kAbM%q*n(pubvr+VfoDCz{_^$)ZynbtFb+Q6Qm5Vj5(6@>fPTBXV;DPq>2#>Nvee-QHc08gX<VgtxBMU`~sh>Q_D2&NKbqj5Ne
>7P%u5|^Mq+4eytzau3u>fAq=5Mr(r*p<=QVTS*)Ji_5+MGoKf(=CQvvz&M0D6nCr>>lI}QnA5KBw3|s1M9qrQNg3;OZfHy_~4a}
<h?e}MsbNpYSXA8%c_DEA0&__Ww|Zeq2^rJj^HK|^5nsh>Qm=x+1@2$K>uS>eLR`j13M*sCziNfkXK+$R-WhQ)v-!Fk<&-
PnI`!BS5ldKPI0o3rk{97`Jbyr6>pR@NCzWojwO$I02=cl#=!2<7+RE3!77G6f4FbWVUHEZ*NWV@RSbwBqAv`BzOLn0K+VX0LCfm
UNmh5&P9BmRP~~+~%n`<7m7c=zbk;MGjLira<<x*AvdWB$xoCWO8pBwxSr`@CUijU}_r{eWIGu$SM>6=O46CY{#Wnx&r0i@j0~JW
A#4Xh$`#=a&tFW*OVi4Ro3QNFcm6je@0;_zS=ycLvsuE}|MtQVBdVr-cUQ@ktaVX~IsSqL%EyJac+xhH1SK9D>xlC}@tZEvp7o6O
oQwZwpj&+^@b8GlIS4m;kK3;6z$4<e?2_Hr~#r)m&@d=Z8n}tN?N+MOAM6~DtLMhccjofJMLkMQl@2}zzoPYh$;jNHZ<TWXM=K3x
fw1}-
%*%6G*No<CaHRKK%BOjtqSJv^A>smJH!lv6x_Bf8YtrxLu>r70^mS6yR*{z9i!3Wl^GW*sO?P;T=RYzVMU2{0cMxFXlSXiEek!AR
~2(;v2j3`*l)i>JUelH#`XvE^eBJV~|63{wEAn=zi#7Z<*RWU2zWF}$@VI_cbS5#}y;{h-
TY%Iv|fVREZIq8m^VCd)v7&ZOB{G=a!R$(XZzoA9z-
`Z|XziQE|j!OJ83;n4#Uw|59<ma@{6k_&XmztBg^RMX4LrzZJFy)9a3~+N63EfBGEKn!KFo6<wmow<)QlU(4ff*v3q3^|sP`E;}l
^6r1l68#Ik>?>>4~5u9PK9Yrl<tsC8Y9M-$x!q41Eg>YH9#Ft!ST#rIz}Tr0;7a<HS4-
1@&he^d7;Bn01^FrC5KS!>QrR*_@_;@(bNE}WKuDSyxy#!x)pU+fSPFn{^L|+x@t+j(z1djMKyxcc&`Ve{z-q-
&sN3Zdo95q&;q<#24r&ZQ+hP6;h=XE)+hU+^KG@vkotmtj0UekC-
0wn=NI1P@vFh>ercEN(P>W#AK)(p65foWhA#$mF!cQ5ork`;(Qu^Qe(PJ7_SC{^U-d6v;aEl&gTaRNfxH%>=>YZ-
*fnogV{ND{?)dTW&BZyo6{TXkSv&bSzM|?eP5jH#^FKcm8SDGZsx|cb=fPPY{h*swUT6m@u75Q6@dBq1F*CTlENwv0b;i4)W5wBV
{#b~1!u2zWMFcjjp;7y=#2P>&PO1n8dBz~W2y2#JSEkskR2PrD%KlAQ6@^O=^9tK{@qymDb#8Z!{JrMjx!i7KEd*n1u5@IcEkpP-
lSk(31?|ki>@v}^R}^6^I&EeG)8WlkdG@<j2i2e^C3&MqT12neVO=>hmpax|V&@VQSYqI!=`$@`#+d80V`9}=F(|Xgiadyi*|DSX
QVd!Sn8s^|2;bbqsL+RcaAses6Mr5=xaD|UlYZ89!VZbu%rw6)`I}uU8er%zTDWr!ka?yc$cv!AfEyN$z8QW_DFIxNWMcHC41grd
rWVZlByj$NuAyd^E44rttBIDXm>8)W3c{IHl8;gak?n?z8Z;dWf+~hX>51H_86nD|97AfVmDEF|=@pwC3rpZXBd<PEd2w2O#JdNg
ZgNOw8An)Z7IAV|b?dlc^xRra<(U^r=L*{_==@_Qu309(oZquSlJLVu!nbGQDxD!7dduW1%UR%8b8TIcE>y+m9bC^}W^m-
05PT4;QA%3Q{z+U*T0b>;U0c>g4rB6&%a}?m4axu{4#bZ4waTmB%S7jRLo3%?3zOAsqNy6zJFEBY!t@yOS{D%X(5m=V)~VmY?2L)
}RIOQB5}kKs=aEgK8aEDg=<}yrj2NUt#i9doNRdjvgULhoBX3I<*@bA`dw8Lt$Gz}ix^6LRbWmm|rUNX!g2ckEbx|WFbTC}#>Lil
Bv5|7SQS3>boU1Wk5XoUXbtiv(#l^kE2)X|dhD!$%Nz@&k4WsU4b8cWMnNmV{7mf4YbTYhI)Y^!m2+1lBV^Nd!>k4)i!<E^fBYEb
vmU67pr78W*7*~akVjYTz`6AaIAa`{;N)_?^AmICsL}yCpN_}M(UCCMYC{4!MxtF=b?PBmRZ-*DTGXNr8wDO;OLa+R-
sEx;U%tx+rrZu(Lv&?55bFtZmi1Sp!gh+m+BBgtL)O_>oO<%F<q>=AwTfcRL-
Z5_A%6TYo1=I1MaG7#8G2>pZx|w0DBpcadrb<Lso-JVTx^UB|drg_p{zmBxiwRA*-g~I{^-
sL>v(tCpUj}FAC+9#(JSx6#?#=1jOZzgsABQ9F==A&u0AIa3x#(w-
Pno>RNMP!LaK{H+aig<mI=2X(%BHryyi{b2R9fo5Z_g>ZOz#=)Ur~Dk9r_ew;<@=V*O8TSFSiJ?%SkSHYX<ClDUtflPCWP}#3z+-
Pa#Mg4_sf##o+b%Xpo)$!P&|1?8h%$;u2J@@J-
Za=Xq>ESY5M)GP}IIt61f;QJcJJ=c8kmi<PWRUM8$=_su8x_>Y!W%E$3L2`i=}G{bmGq)`CO-
&*>d1!j6@k!hOusXnKg;{A%*uyr%)b820`dIk5kE{lCOYbkb4AsaXEhuy5&$1icU(Oi=|-gd!jcVQ;r0<U>Yvu__QO-RaaIshU|O
_aJ!Oc}wL%cN8y($_~CeJcXYCweP_vhuYR1H>SBOTNZPGr~ZORAvR6?wWczBP8Fc>M3d5gDP2oD-
#GsNAzXwIjj}*<4a}2@+GyIK<dr`Rh|{1>G8Zk6~;ZK&lI<oaVUToe|h4vaH3~VD7Bq#20ujeS*YC-
)T>$!ijnqIqS;bG+q@+;vyqlb38TTqYt*Vhm@_hi0={z7^MxBaO&~g2JiIlz`enlTLyq4+b?K&R(akaWXI`^uh|N!2x2Y%a$!j;C
&uxPc?Ux_|ap1zkIwqs{mdwrE&)Hh+D!-
0k9=~oyFT+^P^fT`vcCB?q>wcax3e07;)!yrDb=w^aniOj~BY|OKS&ah&N7QL`<32$@22%XUhL41<(xD^6SsLL?-
45y~_k6xopWO;UA`DeUdb7yU87XYeYL02tDJnIoJIVbWrEag|Sr4c^@n>~MMIa|+C<*9%2p}WjWO#SuBwM#=mHhy`-
ehm30gT;BdLuzUong2k2{pHAG2`9Ppd%CKOVf&<uqCJX2wt8sDlSmQ{!o>DSIXHkS9}{_x?%#9RM`+z*^qa9BUM@#eKS?+`@S2-
o#EEC*mOa9d#~GeZLUgLEzl)n*o?$szoeSU;A>qIV<@-wT`?u<tsi)pRG~_ye5n1<zCniXLYsU5`Q5J0x>fzjYUD*Uxr-ma^*uB~
GgHUQ)ENbVyn<V4q;gd)!l69xMifT}03^`~S*ggFfMlpDL-
%5?K0c*R)hU^7eG$#Z>??5A7UJt{0Q}^9xE9c`MiIPWkg8<vhqG?lF)C^(tFYp5W}XXeNag@jGoe;4$TZhKHp7uGHGe~f4k~*zuZ
>YHZhCRd+CkYj$GEkOQ(9kQJkQ;DoO8=^&JWeU%mpo!8IBb`3T%^A;}g5R`OcQQJV=3_ZaVo;=K~P*taAtG6Ylm&b~ktAy_V0<CT
B`_$i4u^?A((#qZA@mp8dCOO6fi52G!+9_8MiTRK7kfozYaqh^dR>xs__wYOGRZ?#Rs5tY*w)@3dM|TAz~qs7fjPl{c^VC@P?LsL
~?BzHD4hwU%w<761u@^4d<`_#4JqD#Tnv?grN4=69Q|ZL`C|YGOsyK690erZ-;X>qk|1Pt-SA?V_Iri(Rg3v7E&!Hdb!ws?06NwX
1Ob$V=9tT!6MzlF{@^WD$fakQ&~e4M%?<kwMz(xVt#0@~i8r*4WCKk0p_s%T*WC>JFC_jKp@SaOBd_yV2m1Z23|x5<wB~Jmw;3=9
26|T(*1E-QF7Pw0BNQnm3tS|Ly42`Ni-rgHqs)SdoT*9@nuZpn+JkiBXZC+H7Qhlo9$V7a=N5cs11<_-
oyCUqI0IheG+=xZZT5dz08Ef5<odifpb(#3cc2{->*g57#vvf4HVDGuX|j$+#xGW<)CDeR2g?naDUfaU(Zc+-
*qvM54T|Qd^}JbiwH)(Y|mCD9D0<OuILA>lmVn%Q##gZKCFYY3y)ACo>n5TjAkazg5mP#f6nkOcl>s$%;*4Sx-Sv^<Jx{rt_mGW=
MZE9RfXTUNlVJ7t>R7VziTSiS!iSHB83()RS1#5Ts!%-
rv)hv6Wt0OK9CBLFsN0tY+f&GFY+l?DGPxRIvzWCF52_?TX@?$ikc4Crw=Vn%~GbO%N=A)~fBgDkQdeN}~a+0}uF9{){!YSM6eue
a1aV{dT@{()(rDbE2F1A`UC&WJ@5+hPsRwH)yQEABaDsVH!P00NdtN4hH6-
sU{CgP{?;<`M@uzCAu;Q7`2}Q3MDYA6FzYi!DMwWKo*fu&4SND1{A%oJ08-z(OA_6z^fP+%ll>!hD-cWl^-
NuKvO+3IPv<5)6FFA^_9F~o^|hrN+*Mx2Iv%MOKG(C8e97f*mke&W6xagl`A}1*A=T%S7JlNkZL*#fWGYvgh-
?02`e3f8c8Okg(rL2J!VTVjAxd|fz$VzcEyIc)=sQ<Bb3SQ9ymsHqvSl~V6#~-n$+eCZNDR@Ow+*-
C|r2X;uAG3r5&>k%<Pb}N0N|g7_friU_3zs*3{qbijb#T23NGg4MZ6x-wdR2yaoXcPfiwa&e1FE=rE>B@hHPAtmUGY!;4F8-
jjB1&ocV4eK6A=$Y&G0Qw-bK-
Oqkh)bAlWV}g3%yGltMfJs1)@~gq|PrzVbzXs`z+@TBfLypeR@es@Dqr8TZe1m~aP!~)Dw%J)Em%EoH-eSr!r?iwViS}gM(#mT(m
Md0tuI{B^ug1cVpI}zPrFB4H4UoE4On#{4CV=EE32$XEcL&07U22$LN3?7mH}Hii#)JdfF#o<0c}=j5DX6F-
L+BAQLbU3tw#0@frUaoW;^Nm;xWYhW{%Y2Igq)F}g@b_8P#R~^#pN`D8%kfn{N6I~3Xcj`EI1nTx2s~;CZn;_wIEHeCIjpmoVaiy
$WKo#a|!43`Fh$hd8rtYB>YWcX`MY@fSMK@32$nan>fFo^1~Hlujh2Ki3yBvJ4L>S;TfLI`tf3Ld0F6rNVEg_(ZZM#F8(0sS{Kof
i452bd0!eZ@r|9J774F$O+G!*n{PC0$-p{(ZzK1yqU=z2Yzrg1k-
=k`g@JIWq#f}lbKpstoX{zUrY7y8!>5dsE^C1jjgz$rh?9EAUAvhr#+b}P3SDbtI0ogU?G5@$LYpC=vCvBA&Hw)I|J}tamb=am`0
zjQVb{1JmM)TZ-
S3=#8UEDx`C{b!8Ks*``c|o2C>_4%y#H}A3qFLi$!!Zd(tw`4uT(Tgw=JOREa3Zx=TO%pRQZ<08po&7hE#(eFX#R;xm}2K&^_nHi
}yn2eE;G_(>WIb?#$i|AY)!o=oy~99bkdV*#aavI)X*Ap%Ksi3FFz{<GjAFJMZ-
@!&BZUk47A^;n){I(j<jJvr>6~^#D`ycnurDKfHJT{$KyMsHP$8Yz@QE=2Sb~R_CBrsWhCw|DXTm9INb)TiY^rl7u?i2s;Pz{zJK
$Ql1-8mS)Ilw>zb>bOvw>M-
sD$Ca(I%g9w~JGz>&)H+cXVDl2NOtMncztHb=N4hrCbDSf=pW@b+soazouH19>qaU+wl5&<GL0!?eflgIZxr+d)q9!PVIF?y{G)S
chLctM_cQO6}2)c^k9{^xN{tfMC1mxpD&*OnDC1Qsj)_y6adp#q^*2ejhiqI$?|LO|pQ|9_pAD9St`FkzB<maO!;qnyab`~nu`jv
#8jD3_M7QWTZA(!9V_seJdHbA<B^Gr)XE(jM|5pz?J*>OCz*V=29OQFl7+_CEke<r|$~Tq+47NP<zSZ$+q7A1oeu^*vAQ_t%d~rO
QGr<LC~G%8OkkVPO&RNgjofpX!xt9Xf}S(G*IYfM@9Cd!(KBHB=HKvGD98KYX`?y3Rq}^ja|(g*Xu-
_==bdU@15it9cyWVAev!iOLh$q?wQfY;9gtpeJJ!rJv`<;Egad$b<Bnwe{~Ru(4X**`;XKCNe6u^n1uIH{8+R=b1wj>UxQriG0(`
ENo()ayjGaBFRE*y<Hws3b4XH6T4AkZrvGRhCf39ZYK3{CC5B}#e2v5jD(=K6CK1e4|r8J1SJ^j5NF9EqcFg242c2z33L8n2x7oY
U~jk0@<p~X+m0kGZQ3lA2x-
9fWUZ^H?AmVa?#dafjQq%n>4$xe;fjhC8Lwol2FXVnYAkGjCXiMiG@R`}w>xZjgDmTp^fFt}B4pYuR3MqGsX%I!R92{zg@C4TPQY
0Ov$*=KafXV1p>;;IAhP|L?y!XG?HrWBmFPiSs#{jdRyG(#HmsiJHHah%$j|OG&0+b<Hr3l|^1e0eqG!7<rRFGL)+LIeGn%iahm1
Qi=U^-o?}hH5$tCCRFH*Ct>%wVu)$R3ZeEFto7pz~=AMN}%(N^yGH-
!25bmog+`SI&(c$rJ$LAKCa#2&4jDmhae+m}i=b8(iZ7nq|8;0))h=9Fkbq>nlSu^B2r+)i9mV5XTZju6n90Xaw@7bB1h2G}GZKq
L{jPkt>{>2ie;0ma#1b3p=ftYR#9A$-~0Wd-f1=!??UGU;zb_zeIreQdCK_aTVlDnH2V4dG{yyu8H+daUUpJiUZszH%*#Xb?-
nPcx7Z58c1c6;&AhuD&QambZ=+l-
J%le1=P3FUlnmo=O9wO5{Ut3g{PAz%WhkMP3)t&qMlu){&)b3v2vy&v3wHdZS!w{h_iDs@^GCrl5ms>bV^CM{h4>&ogC(<U<B$&m
_L`;~M5vXXZoD7Pp`YO9cxUQ9qfJdQSxYkg{r5kU8M?L<L4<fl)`{*~2GlGGYwO;pC4AK2eV)c`=5Jy+WK65-
H8i&Cdia%oO`XnOx>vf^VDPgl&c{%tM(kA<-)f6{iHrmy^g8vXML^W(diqoU-
QJ*z+n~bEd68>d46s7L&Hc2X(U6^dzD7Mvf`iP439uQFgpGcZ@;D6WB5quQ(B7UUI^rSggyR-dSsmUhfilIz5b?zqEVsbe>}irXb
IAyZn%0c}9#cID53oY0+n$jx0ISx%M3C`lG0iYWI!iRX@J@*wcyNoPVY56&-
N!hq!qp&xli;7#h)`4E=8Q<C_&)U*6Cc8J$57O+N@=3+C@tx6$C;qG26)ht<Wx{-
KNZA&?+|`@3taF;>wRl%_rA3(6tSURMlY6B$VtH#wjV-
w}Fi`FPfB@`S^Tx`H{Zpm<Yku~wc6TLLVC@WhRGMl_)nMp)hpOT&_#Fi>82>w0No1e^a^b0>{aiBm!uwTz!=GwFe_Sj&wdqc8B-
lhq70ghDAss|B+sv9NJXS-ooGuut96w+#PONcu)$pjOtsjlw~57%WJ^zVY4$;_h^Y=V<MX?TI`m91#7ce{l(W8lScEj68AmvYha1
FNIjQ4}En8kAh~tGMmj4i32vuTCjNnghwkTzeI<wJLi|;$Iqx;Ju6&aUUinGCrtuJr{~8%WsjO7m%{XgB!v=GN#vJ(Z0G!f>Bb5g
8=n2#KOLU9WqHyt;uQK^+dO;2lW8NKME;{;v4uUoYNT%z7~3R+V=ZepaJDKYtHoM-
<t_12FK!4q!#q9QDrwSYpj<Oor$R0*0l5ug4)n^SG^L(LOUUymot@{37+|*J+~XZsgU?Y~C6Nf)`~OUSY@z"""

raw = zlib.decompress(base64.b85decode("".join(PAYLOAD.split()).encode("ascii")))
if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA256:
    raise SystemExit("BLOCK: Batch-003 subject executor bootstrap digest mismatch")
TARGET.write_bytes(raw)
print(f"MATERIALIZED {TARGET.relative_to(ROOT)} SHA-256={EXPECTED_SHA256}")
