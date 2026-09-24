import Std
set_option warningAsError true

namespace QIKVRT.TEMDDMainLoop

structure StageEvidence where
  compile  : Bool
  bind     : Bool
  resolve  : Bool
  execute  : Bool
  test     : Bool
  observe  : Bool
  readback : Bool
  accept   : Bool
deriving Repr, DecidableEq

def effectAckDone (e : StageEvidence) : Bool :=
  e.compile && e.bind && e.resolve && e.execute &&
  e.test && e.observe && e.readback && e.accept

theorem done_iff_all (e : StageEvidence) :
    effectAckDone e = true ↔
      e.compile = true ∧ e.bind = true ∧ e.resolve = true ∧
      e.execute = true ∧ e.test = true ∧ e.observe = true ∧
      e.readback = true ∧ e.accept = true := by
  cases e with
  | mk c b r x t o rb a =>
      cases c <;> cases b <;> cases r <;> cases x <;>
      cases t <;> cases o <;> cases rb <;> cases a <;> decide

theorem execute_alone_not_done :
    effectAckDone {
      compile := false, bind := false, resolve := false, execute := true,
      test := false, observe := false, readback := false, accept := false
    } = false := by decide

theorem test_alone_not_done :
    effectAckDone {
      compile := false, bind := false, resolve := false, execute := false,
      test := true, observe := false, readback := false, accept := false
    } = false := by decide

theorem observe_alone_not_done :
    effectAckDone {
      compile := false, bind := false, resolve := false, execute := false,
      test := false, observe := true, readback := false, accept := false
    } = false := by decide

#print axioms done_iff_all
#print axioms execute_alone_not_done
#print axioms test_alone_not_done
#print axioms observe_alone_not_done

end QIKVRT.TEMDDMainLoop
