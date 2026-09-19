with Ada.Text_IO; use Ada.Text_IO;
with QIKVRT_Core_Invariant; use QIKVRT_Core_Invariant;
procedure Core_Invariant_Main is
   S : Effect_State;
   function Bit (V : Boolean) return Natural is (if V then 1 else 0);
begin
   for T in Boolean loop
      for B in Boolean loop
         for I in Boolean loop
            for R in Boolean loop
               S := Decide (T,B,I,R);
               Put_Line (Natural'Image(Bit(T)) & Natural'Image(Bit(B)) & Natural'Image(Bit(I)) &
                         Natural'Image(Bit(R)) & Natural'Image(Effect_State'Pos(S)) &
                         Natural'Image(Bit(Ordinary_Release(S))));
            end loop;
         end loop;
      end loop;
   end loop;
end Core_Invariant_Main;
