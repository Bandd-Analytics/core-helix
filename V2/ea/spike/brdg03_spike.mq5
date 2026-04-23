//+------------------------------------------------------------------+
//|                                                brdg03_spike.mq5 |
//|  BRDG-03 go/no-go gate: DLL load + single ZMQ PUB send test     |
//|  Run ONLY on the IC Markets MT5 terminal. Record result in      |
//|  V2/bridge/spike/BRDG03-RESULT.md on the developer machine.     |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics"
#property version   "1.00"
#property strict
#property script_show_inputs

#include <Zmq/Zmq.mqh>

input string InpPythonHost = "127.0.0.1";   // Python listener host
input int    InpSpikePort  = 5599;          // Test port (not production)

//+------------------------------------------------------------------+
//| Script program start function                                    |
//+------------------------------------------------------------------+
void OnStart()
{
   Print("========== BRDG-03 SPIKE STARTING ==========");
   Print("Target: tcp://", InpPythonHost, ":", InpSpikePort);
   Print("MT5 Build: ", TerminalInfoInteger(TERMINAL_BUILD));
   Print("Account: ", AccountInfoString(ACCOUNT_COMPANY), " / ", AccountInfoInteger(ACCOUNT_LOGIN));

   // Step 1: Create ZMQ context (DLL must load here)
   Context ctx;
   Print("SPIKE: Context created OK");

   // Step 2: Create PUB socket
   Socket pub(ctx, ZMQ_PUB);
   Print("SPIKE: PUB socket created OK");

   // Step 3: Bind to test port
   string endpoint = StringFormat("tcp://*:%d", InpSpikePort);
   if(!pub.bind(endpoint)) {
      Print("SPIKE FAIL: bind failed on ", endpoint, " — error ", GetLastError());
      ctx.destroy(0);
      return;
   }
   Print("SPIKE: bound to ", endpoint);

   // Step 4: Build topic + payload byte arrays
   string topicStr = "SPIKE";
   string payloadStr = "BRDG03_SPIKE_OK";
   uchar topicBytes[];
   uchar payloadBytes[];
   StringToCharArray(topicStr, topicBytes, 0, StringLen(topicStr));
   StringToCharArray(payloadStr, payloadBytes, 0, StringLen(payloadStr));

   // Step 5: Give SUB time to connect (ZMQ slow-joiner — PUB drops if no subscriber yet)
   Sleep(1500);

   // Step 6: Send multipart [topic, payload]
   if(!pub.sendMore(topicBytes)) {
      Print("SPIKE FAIL: sendMore(topic) failed — error ", GetLastError());
      pub.unbind(endpoint);
      ctx.destroy(0);
      return;
   }
   if(!pub.send(payloadBytes)) {
      Print("SPIKE FAIL: send(payload) failed — error ", GetLastError());
      pub.unbind(endpoint);
      ctx.destroy(0);
      return;
   }

   Print("SPIKE PASS: libzmq.dll loaded, test message sent, no crash");
   Print("Message sent: topic='", topicStr, "' payload='", payloadStr, "'");

   // Step 7: Let the message drain before unbinding
   Sleep(500);
   pub.unbind(endpoint);
   ctx.destroy(0);
   Print("========== BRDG-03 SPIKE COMPLETE ==========");
}
//+------------------------------------------------------------------+
