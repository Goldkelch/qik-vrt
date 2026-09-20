package body Full_Snapshot with SPARK_Mode is
   function Decide (M : Mask; R, D : Enum_Value) return State is
   begin
      if not Valid (R, D) then
         return 5;
      elsif Blocked (M) then
         return 4;
      elsif not Checkable (M) then
         return 0;
      elsif Bit (M, 17) then
         return 4;
      elsif D = 4 then
         return 4;
      elsif D = 3 then
         return 3;
      elsif Ready (M, R, D) then
         return 2;
      else
         return 1;
      end if;
   end Decide;

   function Admit (Derived, Declared : State; V : Validators) return Release_Bit is
   begin
      if Derived = 2 and Declared = 2 and V = 511 then
         return 1;
      else
         return 0;
      end if;
   end Admit;
end Full_Snapshot;
