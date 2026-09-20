-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
package Full_Snapshot with SPARK_Mode is
   subtype Mask is Natural range 0 .. 262143;
   subtype Enum_Value is Natural range 0 .. 5;
   subtype State is Natural range 0 .. 5;
   subtype Validators is Natural range 0 .. 511;
   subtype Release_Bit is Natural range 0 .. 1;
   subtype Bit_Index is Natural range 0 .. 17;

   function Bit (M : Mask; N : Bit_Index) return Boolean is
     ((M / (2 ** N)) mod 2 = 1);
   function Valid (R, D : Enum_Value) return Boolean is (R < 5 and D < 5);
   function Blocked (M : Mask) return Boolean is (Bit (M, 16) or Bit (M, 12));
   function Checkable (M : Mask) return Boolean is (Bit (M, 1) and Bit (M, 2));
   function Ready (M : Mask; R, D : Enum_Value) return Boolean is
     (Bit (M, 0) and Bit (M, 2) and Bit (M, 3) and Bit (M, 4)
      and Bit (M, 5) and Bit (M, 6) and Bit (M, 7) and R > 0
      and Bit (M, 8) and Bit (M, 9) and Bit (M, 10) and D = 2
      and Bit (M, 11) and not Bit (M, 12)
      and Bit (M, 13) and Bit (M, 14) and Bit (M, 15));

   function Decide (M : Mask; R, D : Enum_Value) return State
     with Global => null,
       Post =>
         (if not Valid (R, D) then Decide'Result = 5
          elsif Blocked (M) then Decide'Result = 4
          elsif not Checkable (M) then Decide'Result = 0
          elsif Bit (M, 17) or D = 4 then Decide'Result = 4
          elsif D = 3 then Decide'Result = 3
          elsif Ready (M, R, D) then Decide'Result = 2
          else Decide'Result = 1)
         and then
         ((Decide'Result = 2) =
           (Valid (R, D) and not Blocked (M) and Checkable (M)
            and not Bit (M, 17) and D /= 4 and D /= 3 and Ready (M, R, D)));

   function Admit (Derived, Declared : State; V : Validators) return Release_Bit
     with Global => null,
       Post => ((Admit'Result = 1) = (Derived = 2 and Declared = 2 and V = 511));
end Full_Snapshot;
