//+------------------------------------------------------------------+
//|                                                brdg03_spike.mq5 |
//|  BRDG-03 go/no-go gate: DLL load + single ZMQ PUB send test     |
//|  Run ONLY on the IC Markets MT5 terminal. Record result in      |
//|  V2/bridge/spike/BRDG03-RESULT.md on the developer machine.     |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics"
#property version   "1.00"
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

   // Step 3: Connect to Python SUB listener (listener binds, publisher connects)
   string endpoint = StringFormat("tcp://%s:%d", InpPythonHost, InpSpikePort);
   if(!pub.connect(endpoint))
     {
      Print("SPIKE FAIL: connect failed on ", endpoint, " - error ", GetLastError());
      return;
     }
   Print("SPIKE: connected to ", endpoint);

   // Step 4: Give SUB time to connect (ZMQ slow-joiner - PUB drops if no subscriber yet)
   Sleep(1500);

   // Step 5: Send multipart [topic, payload] using string overloads
   if(!pub.sendMore("SPIKE"))
     {
      Print("SPIKE FAIL: sendMore(topic) failed - error ", GetLastError());
      pub.disconnect(endpoint);
      return;
     }
   if(!pub.send("BRDG03_SPIKE_OK"))
     {
      Print("SPIKE FAIL: send(payload) failed - error ", GetLastError());
      pub.disconnect(endpoint);
      return;
     }

   Print("SPIKE PASS: libzmq.dll loaded, test message sent, no crash");

   // Step 6: Let the message drain before disconnecting. Context auto-destroys on scope exit.
   Sleep(500);
   pub.disconnect(endpoint);
   Print("========== BRDG-03 SPIKE COMPLETE ==========");
}
//+------------------------------------------------------------------+
