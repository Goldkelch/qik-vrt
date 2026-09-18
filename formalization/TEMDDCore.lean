namespace QIKVRT.TEMDD
inductive State where | hold | continue | successorRequired | done deriving DecidableEq
inductive Event where | unknown | evidence | blocker deriving DecidableEq
def transition : State -> Event -> State
| State.done, _ => State.done
| _, Event.blocker => State.successorRequired
| _, Event.evidence => State.continue
| _, Event.unknown => State.hold
structure DoD where
 zeroBugs : Bool
 allPullRequestsRegarded : Bool
 allBranchesRegarded : Bool
 allProductiveBranchesMerged : Bool
 freshExactMainValidationPass : Bool
 freshEffectReadback : Bool
def complete (d : DoD) : Bool := d.zeroBugs && d.allPullRequestsRegarded && d.allBranchesRegarded && d.allProductiveBranchesMerged && d.freshExactMainValidationPass && d.freshEffectReadback
theorem blocker_requires_successor (s : State) (h : s != State.done) : transition s Event.blocker = State.successorRequired := by cases s <;> simp [transition] at h ⊢
theorem missing_effect_readback_not_done (d : DoD) (h : d.freshEffectReadback = false) : complete d = false := by simp [complete, h]
end QIKVRT.TEMDD
