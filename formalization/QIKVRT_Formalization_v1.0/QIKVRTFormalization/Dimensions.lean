import QIKVRTFormalization.Quantizability

/-!
# SI dimensional algebra

Dimensions are exponent vectors over the seven SI base dimensions.  These
checks prove homogeneity only; they do not derive dynamics or empirical truth.
-/

namespace QIKVRT

public structure Dimension where
  mass : Int
  length : Int
  time : Int
  current : Int
  temperature : Int
  amount : Int
  luminousIntensity : Int
deriving DecidableEq, Repr, BEq

namespace Dimension

@[expose] public def zero : Dimension := ⟨0, 0, 0, 0, 0, 0, 0⟩

@[expose] public def add (a b : Dimension) : Dimension :=
  ⟨a.mass + b.mass, a.length + b.length, a.time + b.time,
   a.current + b.current, a.temperature + b.temperature,
   a.amount + b.amount, a.luminousIntensity + b.luminousIntensity⟩

@[expose] public def neg (a : Dimension) : Dimension :=
  ⟨-a.mass, -a.length, -a.time, -a.current, -a.temperature,
   -a.amount, -a.luminousIntensity⟩

@[expose] public def sub (a b : Dimension) : Dimension := add a (neg b)

@[expose] public def scale (k : Int) (a : Dimension) : Dimension :=
  ⟨k * a.mass, k * a.length, k * a.time, k * a.current,
   k * a.temperature, k * a.amount, k * a.luminousIntensity⟩

@[expose] public def M : Dimension := ⟨1, 0, 0, 0, 0, 0, 0⟩
@[expose] public def L : Dimension := ⟨0, 1, 0, 0, 0, 0, 0⟩
@[expose] public def T : Dimension := ⟨0, 0, 1, 0, 0, 0, 0⟩
@[expose] public def Theta : Dimension := ⟨0, 0, 0, 0, 1, 0, 0⟩

@[expose] public def speed : Dimension := sub L T
@[expose] public def acceleration : Dimension := sub L (scale 2 T)
@[expose] public def energy : Dimension := add M (sub (scale 2 L) (scale 2 T))
@[expose] public def action : Dimension := add M (sub (scale 2 L) T)
@[expose] public def hbar : Dimension := action
@[expose] public def gravConstant : Dimension := sub (scale 3 L) (add M (scale 2 T))
@[expose] public def curvature : Dimension := scale (-2) L
@[expose] public def stressEnergy : Dimension := add M (sub (scale (-1) L) (scale 2 T))
@[expose] public def area : Dimension := scale 2 L

@[expose] public def einsteinRHS : Dimension :=
  add (sub gravConstant (scale 4 speed)) stressEnergy

@[expose] public def planckLengthSquared : Dimension :=
  sub (add hbar gravConstant) (scale 3 speed)

@[expose] public def planckTimeSquared : Dimension :=
  sub (add hbar gravConstant) (scale 5 speed)

@[expose] public def planckMassSquared : Dimension :=
  sub (add hbar speed) gravConstant

@[expose] public def normalizedHorizonEntropy : Dimension :=
  sub (add (scale 3 speed) area) (add hbar gravConstant)

public theorem einsteinEquationHomogeneous : einsteinRHS = curvature := by decide

public theorem actionHasHbarDimension : action = hbar := rfl

public theorem planckLengthSquaredDimension : planckLengthSquared = scale 2 L := by decide

public theorem planckTimeSquaredDimension : planckTimeSquared = scale 2 T := by decide

public theorem planckMassSquaredDimension : planckMassSquared = scale 2 M := by decide

public theorem horizonEntropyOverBoltzmannIsDimensionless :
    normalizedHorizonEntropy = zero := by decide

end Dimension
end QIKVRT
