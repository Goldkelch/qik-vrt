import QIKVRTFormalization.Definitions.Manuscript
import QIKVRTFormalization.Completion.OpenClaims

/-!
# Completion claim registry

Every constructor below carries the proof of the exact proposition indexed by
its manuscript claim identifier. A registry value cannot be created without the
corresponding kernel proof. `GAT-003` deliberately reuses the pre-existing
Batch04 registry entry rather than introducing a duplicate constructor.
-/

namespace QIKVRT.V2.Claims

inductive CompletionClaimId where
  | def001 | def002 | def003 | def004 | def005
  | def006 | def007 | def008 | def009 | def010
  | def011 | def012 | def013 | def014 | def015
  | def016 | def017 | def018 | def019 | def020
  | esc004 | esc005 | esc003
  | qua004 | qua005 | qua003
  | gat007
  | dim006 | dim007
  deriving DecidableEq, Repr, BEq

structure CheckedCompletionClaim (id : CompletionClaimId)
    (statement : Prop) : Type where
  checked : statement

def completionClaimIds : List CompletionClaimId :=
  [.def001, .def002, .def003, .def004, .def005,
   .def006, .def007, .def008, .def009, .def010,
   .def011, .def012, .def013, .def014, .def015,
   .def016, .def017, .def018, .def019, .def020,
   .esc004, .esc005, .esc003,
   .qua004, .qua005, .qua003,
   .gat007, .dim006, .dim007]

theorem completionClaimIds_count : completionClaimIds.length = 29 := by
  decide

theorem completionClaimIds_pairwise : completionClaimIds.Pairwise (· ≠ ·) := by
  decide

open Definitions Completion

def DEF001 : CheckedCompletionClaim .def001 Definitions.DEF001Statement :=
  ⟨Definitions.DEF001_checked⟩
def DEF002 : CheckedCompletionClaim .def002 Definitions.DEF002Statement :=
  ⟨Definitions.DEF002_checked⟩
def DEF003 : CheckedCompletionClaim .def003 Definitions.DEF003Statement :=
  ⟨Definitions.DEF003_checked⟩
def DEF004 : CheckedCompletionClaim .def004 Definitions.DEF004Statement :=
  ⟨Definitions.DEF004_checked⟩
def DEF005 : CheckedCompletionClaim .def005 Definitions.DEF005Statement :=
  ⟨Definitions.DEF005_checked⟩
def DEF006 : CheckedCompletionClaim .def006 Definitions.DEF006Statement :=
  ⟨Definitions.DEF006_checked⟩
def DEF007 : CheckedCompletionClaim .def007 Definitions.DEF007Statement :=
  ⟨Definitions.DEF007_checked⟩
def DEF008 : CheckedCompletionClaim .def008 Definitions.DEF008Statement :=
  ⟨Definitions.DEF008_checked⟩
def DEF009 : CheckedCompletionClaim .def009 Definitions.DEF009Statement :=
  ⟨Definitions.DEF009_checked⟩
def DEF010 : CheckedCompletionClaim .def010 Definitions.DEF010Statement :=
  ⟨Definitions.DEF010_checked⟩
def DEF011 : CheckedCompletionClaim .def011 Definitions.DEF011Statement :=
  ⟨Definitions.DEF011_checked⟩
def DEF012 : CheckedCompletionClaim .def012 Definitions.DEF012Statement :=
  ⟨Definitions.DEF012_checked⟩
def DEF013 : CheckedCompletionClaim .def013 Definitions.DEF013Statement :=
  ⟨Definitions.DEF013_checked⟩
def DEF014 : CheckedCompletionClaim .def014 Definitions.DEF014Statement :=
  ⟨Definitions.DEF014_checked⟩
def DEF015 : CheckedCompletionClaim .def015 Definitions.DEF015Statement :=
  ⟨Definitions.DEF015_checked⟩
def DEF016 : CheckedCompletionClaim .def016 Definitions.DEF016Statement :=
  ⟨Definitions.DEF016_checked⟩
def DEF017 : CheckedCompletionClaim .def017 Definitions.DEF017Statement :=
  ⟨Definitions.DEF017_checked⟩
def DEF018 : CheckedCompletionClaim .def018 Definitions.DEF018Statement :=
  ⟨Definitions.DEF018_checked⟩
def DEF019 : CheckedCompletionClaim .def019 Definitions.DEF019Statement :=
  ⟨Definitions.DEF019_checked⟩
def DEF020 : CheckedCompletionClaim .def020 Definitions.DEF020Statement :=
  ⟨Definitions.DEF020_checked⟩

def ESC004 : CheckedCompletionClaim .esc004 Completion.ESC004Statement :=
  ⟨Completion.ESC004_checked⟩
def ESC005 : CheckedCompletionClaim .esc005 Completion.ESC005Statement :=
  ⟨Completion.ESC005_checked⟩
def ESC003 : CheckedCompletionClaim .esc003 Completion.ESC003Statement :=
  ⟨Completion.ESC003_checked⟩
def QUA004 : CheckedCompletionClaim .qua004 Completion.QUA004Statement :=
  ⟨Completion.QUA004_checked⟩
def QUA005 : CheckedCompletionClaim .qua005 Completion.QUA005Statement :=
  ⟨Completion.QUA005_checked⟩
def QUA003 : CheckedCompletionClaim .qua003 Completion.QUA003Statement :=
  ⟨Completion.QUA003_checked⟩
def GAT007 : CheckedCompletionClaim .gat007 Completion.GAT007Statement :=
  ⟨Completion.GAT007_checked⟩
def DIM006 : CheckedCompletionClaim .dim006 Completion.DIM006Statement :=
  ⟨Completion.DIM006_checked⟩
def DIM007 : CheckedCompletionClaim .dim007 Completion.DIM007Statement :=
  ⟨Completion.DIM007_checked⟩

end QIKVRT.V2.Claims
