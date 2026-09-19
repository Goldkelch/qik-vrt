package QIKVRT_Core_Invariant with SPARK_Mode => On is
   type Effect_State is (EFFECT_NACK,EFFECT_ACK_CONTINUE,EFFECT_ACK_DONE,EFFECT_ACK_ISOLATE,EFFECT_ACK_BLOCK);
   function Decide (Transport_Ack, Block_Required, Isolate_Required, Release_Ready : Boolean) return Effect_State
   with Global => null,
     Contract_Cases =>
       (not Transport_Ack => Decide'Result = EFFECT_NACK,
        Transport_Ack and Block_Required => Decide'Result = EFFECT_ACK_BLOCK,
        Transport_Ack and not Block_Required and Isolate_Required => Decide'Result = EFFECT_ACK_ISOLATE,
        Transport_Ack and not Block_Required and not Isolate_Required and Release_Ready => Decide'Result = EFFECT_ACK_DONE,
        Transport_Ack and not Block_Required and not Isolate_Required and not Release_Ready => Decide'Result = EFFECT_ACK_CONTINUE);
   function Ordinary_Release (State : Effect_State) return Boolean
   with Global => null, Post => Ordinary_Release'Result = (State = EFFECT_ACK_DONE);
end QIKVRT_Core_Invariant;
