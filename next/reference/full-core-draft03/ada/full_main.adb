with Ada.Streams;
with Ada.Streams.Stream_IO;
with Full_Snapshot;
procedure Full_Main is
   use Full_Snapshot;
   use Ada.Streams;
   Output : Ada.Streams.Stream_IO.File_Type;
   Row : Stream_Element_Array (1 .. 36);
   Index : Stream_Element_Offset;
   Admission_Row : Stream_Element_Array (1 .. 512);
begin
   Ada.Streams.Stream_IO.Create (Output, Ada.Streams.Stream_IO.Out_File, "full-ada.out");
   for M in Mask loop
      Index := 1;
      for R in Enum_Value loop
         for D in Enum_Value loop
            Row (Index) := Stream_Element (48 + Decide (M, R, D));
            Index := Index + 1;
         end loop;
      end loop;
      Ada.Streams.Stream_IO.Write (Output, Row);
   end loop;
   for Derived in State loop
      for Declared in State loop
         for V in Validators loop
            Admission_Row (Stream_Element_Offset (V) + 1) :=
              Stream_Element (48 + Admit (Derived, Declared, V));
         end loop;
         Ada.Streams.Stream_IO.Write (Output, Admission_Row);
      end loop;
   end loop;
   Ada.Streams.Stream_IO.Close (Output);
end Full_Main;
