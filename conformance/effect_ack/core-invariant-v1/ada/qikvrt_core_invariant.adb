package body QIKVRT_Core_Invariant with SPARK_Mode => On is
   function Decide (Transport_Ack, Block_Required, Isolate_Required, Release_Ready : Boolean) return Effect_State is
   begin
      if not Transport_Ack then return EFFECT_NACK;
      elsif Block_Required then return EFFECT_ACK_BLOCK;
      elsif Isolate_Required then return EFFECT_ACK_ISOLATE;
      elsif Release_Ready then return EFFECT_ACK_DONE;
      else return EFFECT_ACK_CONTINUE;
      end if;
   end Decide;
   function Ordinary_Release (State : Effect_State) return Boolean is
   begin
      return State = EFFECT_ACK_DONE;
   end Ordinary_Release;
end QIKVRT_Core_Invariant;
