-- SPDX-License-Identifier: CC-BY-NC-ND-4.0
-- Copyright (c) 2026 Ingolf Lohmann.

import QIKVRTFormalization.Meta.TEMDDConservativeUniversality

namespace QIKVRT.V2.Claims

structure CheckedTEMDDConservativeUniversality where
  checked : TEMDD.TEMDDConservativeUniversalityStatement

def TEMDDConservativeUniversality :
    CheckedTEMDDConservativeUniversality :=
  ⟨TEMDD.TEMDDConservativeUniversality_checked⟩

end QIKVRT.V2.Claims
