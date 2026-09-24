-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
package TEMDD_Main_Loop with SPARK_Mode is
   type Stage_Evidence is record
      Compile  : Boolean;
      Bind     : Boolean;
      Resolve  : Boolean;
      Execute  : Boolean;
      Test     : Boolean;
      Observe  : Boolean;
      Readback : Boolean;
      Accept   : Boolean;
   end record;

   function Effect_Ack_Done (E : Stage_Evidence) return Boolean is
     (E.Compile and E.Bind and E.Resolve and E.Execute and
      E.Test and E.Observe and E.Readback and E.Accept)
     with Global => null;

   function Advance_Allowed (E : Stage_Evidence; Successor_Bound : Boolean)
     return Boolean is
     (Effect_Ack_Done (E) and Successor_Bound)
     with Global => null;
end TEMDD_Main_Loop;
