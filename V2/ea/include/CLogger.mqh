//+------------------------------------------------------------------+
//|                                                      CLogger.mqh |
//|                         MT5 POC - CSV Trade Logger Class         |
//|                         v2.1: Added Telegram push notifications  |
//+------------------------------------------------------------------+
#property copyright "Bandd Analytics"
#property link      "https://www.example.com"
#property version   "2.10"

#ifndef CLOGGER_H
#define CLOGGER_H

//--- Trade log entry structure
struct STradeLogEntry
{
   datetime  entryTime;
   string    symbol;
   int       direction;      // 1=long, -1=short
   double    lotSize;
   double    entryPrice;
   double    stopLoss;
   double    takeProfit;
   double    signalScore;    // 0-100
   int       regimeCode;
   string    comment;
};

//--- CSV + Telegram Logger
class CLogger
{
private:
   int       fileHandle;
   string    fileName;
   bool      isOpen;
   string    csvHeader;

   // Telegram state
   string    telegramToken;
   string    telegramChatId;
   bool      telegramEnabled;

public:
   CLogger();
   ~CLogger();

   bool    Init(string logFileName = "MarketMind_Journal");
   void    Close();

   // Telegram initialisation — call after Init() if notifications are wanted.
   // NOTE: Add "https://api.telegram.org" to MT5 allowed URLs:
   //   Tools → Options → Expert Advisors → Allow WebRequest for listed URL
   bool    InitTelegram(string botToken, string chatId);

   void    LogTrade(STradeLogEntry &entry, bool sendAlert = false);
   void    LogEvent(datetime eventTime, string eventType, string message,
                    bool sendAlert = false);
   void    LogCircuitBreakerTrip(string reason);   // Always sends Telegram

   bool    IsOpen()      { return isOpen; }
   string  GetFileName() { return fileName; }

private:
   string  FormatCSVLine(STradeLogEntry &entry);
   string  GetDateTimeString(datetime dt);
   void    SendTelegram(string message);
   string  BuildTelegramText(STradeLogEntry &entry);
};

//+------------------------------------------------------------------+
CLogger::CLogger()
   : fileHandle(INVALID_HANDLE),
     isOpen(false),
     telegramEnabled(false)
{
   csvHeader = "DateTime,Symbol,Direction,Lots,EntryPrice,StopLoss,TakeProfit,"
               "SignalScore,RegimeCode,Comment\n";
}

//+------------------------------------------------------------------+
CLogger::~CLogger()
{
   Close();
}

//+------------------------------------------------------------------+
bool CLogger::Init(string logFileName)
{
   if(isOpen) Close();

   fileName = logFileName + "_" + TimeToString(TimeCurrent(), TIME_DATE) + ".csv";

   if(FileIsExist(fileName))
      fileHandle = FileOpen(fileName, FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI);
   else
   {
      fileHandle = FileOpen(fileName, FILE_WRITE | FILE_CSV | FILE_ANSI);
      if(fileHandle != INVALID_HANDLE)
         FileWriteString(fileHandle, csvHeader);
   }

   if(fileHandle == INVALID_HANDLE)
   {
      Print("CLogger: Cannot open log file: ", fileName);
      isOpen = false;
      return false;
   }

   isOpen = true;
   FileSeek(fileHandle, 0, SEEK_END);
   return true;
}

//+------------------------------------------------------------------+
bool CLogger::InitTelegram(string botToken, string chatId)
{
   if(StringLen(botToken) == 0 || StringLen(chatId) == 0)
   {
      Print("CLogger: Telegram init skipped — empty token or chat ID");
      telegramEnabled = false;
      return false;
   }
   telegramToken   = botToken;
   telegramChatId  = chatId;
   telegramEnabled = true;

   // Send a startup ping to confirm connectivity
   SendTelegram("MarketMind EA started — " +
                TimeToString(TimeCurrent(), TIME_DATE | TIME_MINUTES));
   return true;
}

//+------------------------------------------------------------------+
void CLogger::Close()
{
   if(fileHandle != INVALID_HANDLE)
   {
      FileClose(fileHandle);
      fileHandle = INVALID_HANDLE;
   }
   isOpen = false;
}

//+------------------------------------------------------------------+
void CLogger::LogTrade(STradeLogEntry &entry, bool sendAlert)
{
   if(isOpen)
   {
      FileWriteString(fileHandle, FormatCSVLine(entry));
      FileFlush(fileHandle);
   }

   if(sendAlert && telegramEnabled)
      SendTelegram(BuildTelegramText(entry));
}

//+------------------------------------------------------------------+
void CLogger::LogEvent(datetime eventTime, string eventType, string message,
                        bool sendAlert)
{
   if(isOpen)
   {
      string timeStr = GetDateTimeString(eventTime);
      string line    = timeStr + "," + eventType + ",,,,,,,," + message + "\n";
      FileWriteString(fileHandle, line);
      FileFlush(fileHandle);
   }

   if(sendAlert && telegramEnabled)
      SendTelegram("[" + eventType + "] " + message);
}

//+------------------------------------------------------------------+
//| Circuit breaker events always push to Telegram regardless of flag|
//+------------------------------------------------------------------+
void CLogger::LogCircuitBreakerTrip(string reason)
{
   string eventType = "CIRCUIT_BREAKER";
   LogEvent(TimeCurrent(), eventType, reason, false);

   if(telegramEnabled)
      SendTelegram("CIRCUIT BREAKER TRIPPED\n" + reason +
                   "\n" + TimeToString(TimeCurrent(), TIME_DATE | TIME_MINUTES));
}

//+------------------------------------------------------------------+
//| Send a message via Telegram Bot API using WebRequest             |
//+------------------------------------------------------------------+
void CLogger::SendTelegram(string message)
{
   if(!telegramEnabled) return;

   string url  = "https://api.telegram.org/bot" + telegramToken + "/sendMessage";
   string body = "{\"chat_id\":\"" + telegramChatId + "\","
                 "\"text\":\"" + message + "\","
                 "\"parse_mode\":\"HTML\"}";

   char   postData[];
   char   result[];
   string headers = "Content-Type: application/json\r\n";
   string responseHeaders;

   StringToCharArray(body, postData, 0, StringLen(body));

   int httpStatus = WebRequest("POST", url, headers, 5000, postData,
                               result, responseHeaders);

   if(httpStatus != 200)
      Print("CLogger: Telegram WebRequest failed, HTTP status=", httpStatus);
}

//+------------------------------------------------------------------+
//| Format trade entry for Telegram                                  |
//+------------------------------------------------------------------+
string CLogger::BuildTelegramText(STradeLogEntry &entry)
{
   string dir = (entry.direction > 0) ? "LONG" : "SHORT";
   return "<b>" + entry.symbol + " " + dir + "</b>\n"
          + "Lots: "   + DoubleToString(entry.lotSize, 2)   + "\n"
          + "Entry: "  + DoubleToString(entry.entryPrice, 5) + "\n"
          + "SL: "     + DoubleToString(entry.stopLoss, 5)   + "\n"
          + "TP: "     + DoubleToString(entry.takeProfit, 5) + "\n"
          + "Score: "  + DoubleToString(entry.signalScore, 1) + "\n"
          + "Regime: " + IntegerToString(entry.regimeCode)   + "\n"
          + entry.comment;
}

//+------------------------------------------------------------------+
string CLogger::FormatCSVLine(STradeLogEntry &entry)
{
   string timeStr = GetDateTimeString(entry.entryTime);
   string dir     = (entry.direction > 0) ? "LONG" : "SHORT";

   return timeStr + ","
          + entry.symbol + ","
          + dir + ","
          + DoubleToString(entry.lotSize, 2)    + ","
          + DoubleToString(entry.entryPrice, 5) + ","
          + DoubleToString(entry.stopLoss, 5)   + ","
          + DoubleToString(entry.takeProfit, 5) + ","
          + DoubleToString(entry.signalScore, 2) + ","
          + IntegerToString(entry.regimeCode)    + ","
          + entry.comment + "\n";
}

//+------------------------------------------------------------------+
string CLogger::GetDateTimeString(datetime dt)
{
   return TimeToString(dt, TIME_DATE) + " " + TimeToString(dt, TIME_MINUTES);
}

#endif
