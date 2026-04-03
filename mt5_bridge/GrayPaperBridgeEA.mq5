#property strict
#property version   "1.100"
#property description "Gray MT5 paper bridge scaffold"
#property description "Reads JSON tickets from MQL5/Files/gray_bridge/inbox and writes results to outbox."

input string InpBridgeRoot = "gray_bridge";
input int    InpPollSeconds = 5;
input ulong  InpMagicNumber = 26032601;
input bool   InpPaperOnly = true;

#define MAX_TICKET_ENTRIES 8

struct BridgeTicket
{
   string ticket_id;
   string created_at;
   string mode;
   string symbol;
   string side;
   string order_plan;
   int    entry_count;
   string entry_types[MAX_TICKET_ENTRIES];
   double entry_prices[MAX_TICKET_ENTRIES];
   double volume_lots[MAX_TICKET_ENTRIES];
   string client_entry_ids[MAX_TICKET_ENTRIES];
   double stop_loss;
   double take_profit;
   bool   trailing_enabled;
   double trailing_activation_price;
   double trailing_distance_price;
   double trailing_step_price;
   string trailing_distance_mode;
   double trailing_distance_value;
   int    trailing_atr_period;
   string trailing_atr_timeframe;
   double max_risk_usdt;
   string note;
   string raw_json;
   string file_name;
};

struct TrailingConfig
{
   string ticket_id;
   string symbol;
   string side;
   ulong  order_id;
   bool   enabled;
   double trigger_price;
   string distance_mode;
   double distance_value;
   double step_price;
   int    atr_period;
   string atr_timeframe;
};

struct PackageConfig
{
   string ticket_id;
   string symbol;
   string side;
   string order_plan;
   bool   cancel_other_on_fill;
   int    order_count;
   ulong  order_ids[MAX_TICKET_ENTRIES];
};

string BridgeDir(const string leaf)
{
   if(leaf == "")
      return InpBridgeRoot;
   return InpBridgeRoot + "\\" + leaf;
}

string BridgeFile(const string leaf,const string name)
{
   return BridgeDir(leaf) + "\\" + name;
}

bool IsWhitespace(const int ch)
{
   return (ch == ' ' || ch == '\t' || ch == '\r' || ch == '\n');
}

int SkipWhitespace(const string text,int pos)
{
   const int len = StringLen(text);
   while(pos < len && IsWhitespace(StringGetCharacter(text,pos)))
      pos++;
   return pos;
}

string Trim(const string text)
{
   int start = 0;
   int finish = StringLen(text) - 1;

   while(start <= finish && IsWhitespace(StringGetCharacter(text,start)))
      start++;
   while(finish >= start && IsWhitespace(StringGetCharacter(text,finish)))
      finish--;

   if(finish < start)
      return "";

   return StringSubstr(text,start,finish - start + 1);
}

bool IsJsonNumberChar(const int ch)
{
   return ((ch >= '0' && ch <= '9') || ch == '-' || ch == '+' || ch == '.' || ch == 'e' || ch == 'E');
}

bool JsonFindValueStart(const string json,const string key,int &value_pos)
{
   const string needle = "\"" + key + "\"";
   const int key_pos = StringFind(json,needle,0);
   if(key_pos < 0)
      return false;

   const int colon_pos = StringFind(json,":",key_pos + StringLen(needle));
   if(colon_pos < 0)
      return false;

   value_pos = SkipWhitespace(json,colon_pos + 1);
   return true;
}

bool JsonGetString(const string json,const string key,string &value)
{
   int pos = 0;
   if(!JsonFindValueStart(json,key,pos))
      return false;

   if(StringGetCharacter(json,pos) != '"')
      return false;

   int end_pos = pos + 1;
   const int len = StringLen(json);
   while(end_pos < len)
   {
      if(StringGetCharacter(json,end_pos) == '"' && StringGetCharacter(json,end_pos - 1) != '\\')
         break;
      end_pos++;
   }

   if(end_pos >= len)
      return false;

   value = StringSubstr(json,pos + 1,end_pos - pos - 1);
   return true;
}

bool JsonGetNumber(const string json,const string key,double &value)
{
   int pos = 0;
   if(!JsonFindValueStart(json,key,pos))
      return false;

   int end_pos = pos;
   const int len = StringLen(json);
   while(end_pos < len && IsJsonNumberChar(StringGetCharacter(json,end_pos)))
      end_pos++;

   if(end_pos <= pos)
      return false;

   value = StringToDouble(StringSubstr(json,pos,end_pos - pos));
   return true;
}

bool JsonGetBool(const string json,const string key,bool &value)
{
   int pos = 0;
   if(!JsonFindValueStart(json,key,pos))
      return false;

   if(StringSubstr(json,pos,4) == "true")
   {
      value = true;
      return true;
   }

   if(StringSubstr(json,pos,5) == "false")
   {
      value = false;
      return true;
   }

   return false;
}

bool JsonGetObject(const string json,const string key,string &object_json)
{
   int pos = 0;
   if(!JsonFindValueStart(json,key,pos))
      return false;

   if(StringGetCharacter(json,pos) != '{')
      return false;

   int depth = 0;
   const int len = StringLen(json);
   for(int i = pos; i < len; i++)
   {
      const int ch = StringGetCharacter(json,i);
      if(ch == '{')
         depth++;
      else if(ch == '}')
      {
         depth--;
         if(depth == 0)
         {
            object_json = StringSubstr(json,pos,i - pos + 1);
            return true;
         }
      }
   }

   return false;
}

bool JsonGetArray(const string json,const string key,string &array_json)
{
   int pos = 0;
   if(!JsonFindValueStart(json,key,pos))
      return false;

   if(StringGetCharacter(json,pos) != '[')
      return false;

   int depth = 0;
   const int len = StringLen(json);
   for(int i = pos; i < len; i++)
   {
      const int ch = StringGetCharacter(json,i);
      if(ch == '[')
         depth++;
      else if(ch == ']')
      {
         depth--;
         if(depth == 0)
         {
            array_json = StringSubstr(json,pos,i - pos + 1);
            return true;
         }
      }
   }

   return false;
}

int JsonCountTopLevelObjectsInArray(const string array_json)
{
   int depth = 0;
   int count = 0;
   const int len = StringLen(array_json);

   for(int i = 0; i < len; i++)
   {
      const int ch = StringGetCharacter(array_json,i);
      if(ch == '{')
      {
         if(depth == 0)
            count++;
         depth++;
      }
      else if(ch == '}')
      {
         depth--;
      }
   }

   return count;
}

bool JsonGetFirstObjectFromArray(const string array_json,string &object_json)
{
   int pos = StringFind(array_json,"{",0);
   if(pos < 0)
      return false;

   int depth = 0;
   const int len = StringLen(array_json);
   for(int i = pos; i < len; i++)
   {
      const int ch = StringGetCharacter(array_json,i);
      if(ch == '{')
         depth++;
      else if(ch == '}')
      {
         depth--;
         if(depth == 0)
         {
            object_json = StringSubstr(array_json,pos,i - pos + 1);
            return true;
         }
      }
   }

   return false;
}

bool JsonGetObjectFromArrayAtIndex(const string array_json,const int target_index,string &object_json)
{
   object_json = "";
   if(target_index < 0)
      return false;

   int depth = 0;
   int found_index = -1;
   int start_pos = -1;
   const int len = StringLen(array_json);
   for(int i = 0; i < len; i++)
   {
      const int ch = StringGetCharacter(array_json,i);
      if(ch == '{')
      {
         if(depth == 0)
         {
            found_index++;
            if(found_index == target_index)
               start_pos = i;
         }
         depth++;
      }
      else if(ch == '}')
      {
         depth--;
         if(depth == 0 && found_index == target_index && start_pos >= 0)
         {
            object_json = StringSubstr(array_json,start_pos,i - start_pos + 1);
            return true;
         }
      }
   }

   return false;
}

string JsonEscape(string text)
{
   StringReplace(text,"\\","\\\\");
   StringReplace(text,"\"","\\\"");
   StringReplace(text,"\r","\\r");
   StringReplace(text,"\n","\\n");
   return text;
}

string NowIso()
{
   string value = TimeToString(TimeLocal(),TIME_DATE | TIME_SECONDS);
   StringReplace(value,".","-");
   StringReplace(value," ","T");
   return value;
}

string FileSafeStamp()
{
   string value = TimeToString(TimeLocal(),TIME_DATE | TIME_SECONDS);
   StringReplace(value,".","");
   StringReplace(value,":","");
   StringReplace(value," ","_");
   return value;
}

string ULongText(const ulong value)
{
   return StringFormat("%I64u",value);
}

string LongText(const long value)
{
   return StringFormat("%I64d",value);
}

string JsonDoubleOrNull(const double value,const int digits)
{
   if(!MathIsValidNumber(value) || value <= 0.0)
      return "null";
   return DoubleToString(value,digits);
}

int SymbolDigitsFor(const string symbol)
{
   const long digits = SymbolInfoInteger(symbol,SYMBOL_DIGITS);
   if(digits < 0)
      return 5;
   return (int)digits;
}

string JsonBool(const bool value)
{
   return value ? "true" : "false";
}

string NormalizeMode(const string raw_mode)
{
   string mode = raw_mode;
   StringToLower(mode);
   return mode;
}

int ParseTimeframeText(const string raw_text)
{
   string text = raw_text;
   StringToUpper(text);

   if(text == "M1")  return PERIOD_M1;
   if(text == "M5")  return PERIOD_M5;
   if(text == "M15") return PERIOD_M15;
   if(text == "M30") return PERIOD_M30;
   if(text == "H1")  return PERIOD_H1;
   if(text == "H4")  return PERIOD_H4;
   if(text == "D1")  return PERIOD_D1;
   if(text == "W1")  return PERIOD_W1;
   if(text == "MN1") return PERIOD_MN1;

   return PERIOD_CURRENT;
}

string TimeframeToText(const int timeframe)
{
   switch(timeframe)
   {
      case PERIOD_M1:  return "M1";
      case PERIOD_M5:  return "M5";
      case PERIOD_M15: return "M15";
      case PERIOD_M30: return "M30";
      case PERIOD_H1:  return "H1";
      case PERIOD_H4:  return "H4";
      case PERIOD_D1:  return "D1";
      case PERIOD_W1:  return "W1";
      case PERIOD_MN1: return "MN1";
      default:         return "CURRENT";
   }
}

string FileSafeName(string text)
{
   StringReplace(text,"\\","-");
   StringReplace(text,"/","-");
   StringReplace(text,":","-");
   StringReplace(text,"*","-");
   StringReplace(text,"?","-");
   StringReplace(text,"\"","-");
   StringReplace(text,"<","-");
   StringReplace(text,">","-");
   StringReplace(text,"|","-");
   StringReplace(text," ","-");
   return text;
}

string TrailingConfigFileName(const string ticket_id)
{
   return FileSafeName(ticket_id) + "__trailing.json";
}

string PackageConfigFileName(const string ticket_id)
{
   return FileSafeName(ticket_id) + "__package.json";
}

bool ReadTextFile(const string relative_path,string &text)
{
   text = "";
   const int handle = FileOpen(relative_path,FILE_READ | FILE_BIN);
   if(handle == INVALID_HANDLE)
      return false;

   const int size = (int)FileSize(handle);
   uchar buffer[];
   ArrayResize(buffer,size);
   if(size > 0)
      FileReadArray(handle,buffer,0,size);
   FileClose(handle);

   text = CharArrayToString(buffer,0,size,CP_UTF8);
   if(text == "" && size > 0)
      text = CharArrayToString(buffer,0,size);

   return true;
}

bool WriteTextFile(const string relative_path,const string text)
{
   const int handle = FileOpen(relative_path,FILE_WRITE | FILE_BIN);
   if(handle == INVALID_HANDLE)
      return false;

   uchar buffer[];
   const int count = StringToCharArray(text,buffer,0,StringLen(text),CP_UTF8);
   if(count > 0)
      FileWriteArray(handle,buffer,0,count);
   FileClose(handle);
   return true;
}

bool EnsureBridgeFolders()
{
   bool ok = true;
   ok = FolderCreate(InpBridgeRoot) && ok;
   ok = FolderCreate(BridgeDir("inbox")) && ok;
   ok = FolderCreate(BridgeDir("outbox")) && ok;
   ok = FolderCreate(BridgeDir("archive")) && ok;
   ok = FolderCreate(BridgeDir("errors")) && ok;
   ok = FolderCreate(BridgeDir("trailing")) && ok;
   ok = FolderCreate(BridgeDir("trailing_archive")) && ok;
   return ok;
}

bool CopyInboxFileTo(const string destination_leaf,const BridgeTicket &ticket,string &written_file)
{
   written_file = BridgeFile(destination_leaf,FileSafeStamp() + "__" + ticket.file_name);
   return WriteTextFile(written_file,ticket.raw_json);
}

bool DeleteInboxFile(const BridgeTicket &ticket)
{
   return FileDelete(BridgeFile("inbox",ticket.file_name));
}

bool NormalizePrice(const string symbol,const double raw_price,double &normalized_price)
{
   if(raw_price <= 0.0)
      return false;

   double tick_size = SymbolInfoDouble(symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick_size <= 0.0)
      tick_size = SymbolInfoDouble(symbol,SYMBOL_POINT);

   const int digits = (int)SymbolInfoInteger(symbol,SYMBOL_DIGITS);
   normalized_price = raw_price;
   if(tick_size > 0.0)
      normalized_price = MathRound(raw_price / tick_size) * tick_size;
   normalized_price = NormalizeDouble(normalized_price,digits);
   return true;
}

bool NormalizeVolume(const string symbol,const double raw_volume,double &normalized_volume)
{
   if(raw_volume <= 0.0)
      return false;

   const double vol_step = SymbolInfoDouble(symbol,SYMBOL_VOLUME_STEP);
   const double vol_min  = SymbolInfoDouble(symbol,SYMBOL_VOLUME_MIN);
   const double vol_max  = SymbolInfoDouble(symbol,SYMBOL_VOLUME_MAX);

   normalized_volume = raw_volume;
   if(vol_step > 0.0)
      normalized_volume = MathFloor(raw_volume / vol_step) * vol_step;
   if(vol_min > 0.0 && normalized_volume < vol_min)
      normalized_volume = vol_min;
   if(vol_max > 0.0 && normalized_volume > vol_max)
      normalized_volume = vol_max;

   normalized_volume = NormalizeDouble(normalized_volume,2);
   return (normalized_volume > 0.0);
}

string TradeRetcodeText(const uint retcode)
{
   switch(retcode)
   {
      case 10008: return "TRADE_RETCODE_PLACED";
      case 10009: return "TRADE_RETCODE_DONE";
      case 10010: return "TRADE_RETCODE_DONE_PARTIAL";
      case 10013: return "TRADE_RETCODE_INVALID";
      case 10014: return "TRADE_RETCODE_INVALID_VOLUME";
      case 10015: return "TRADE_RETCODE_INVALID_PRICE";
      case 10016: return "TRADE_RETCODE_INVALID_STOPS";
      case 10017: return "TRADE_RETCODE_TRADE_DISABLED";
      case 10018: return "TRADE_RETCODE_MARKET_CLOSED";
      case 10019: return "TRADE_RETCODE_NO_MONEY";
      case 10020: return "TRADE_RETCODE_PRICE_CHANGED";
      case 10021: return "TRADE_RETCODE_PRICE_OFF";
      case 10022: return "TRADE_RETCODE_INVALID_EXPIRATION";
      case 10023: return "TRADE_RETCODE_ORDER_CHANGED";
      case 10024: return "TRADE_RETCODE_TOO_MANY_REQUESTS";
      case 10025: return "TRADE_RETCODE_NO_CHANGES";
      case 10026: return "TRADE_RETCODE_SERVER_DISABLES_AT";
      case 10027: return "TRADE_RETCODE_CLIENT_DISABLES_AT";
      case 10030: return "TRADE_RETCODE_INVALID_FILL";
      case 10031: return "TRADE_RETCODE_CONNECTION";
      case 10032: return "TRADE_RETCODE_ONLY_REAL";
      case 10033: return "TRADE_RETCODE_LIMIT_ORDERS";
      case 10034: return "TRADE_RETCODE_LIMIT_VOLUME";
      case 10035: return "TRADE_RETCODE_INVALID_ORDER";
      case 10036: return "TRADE_RETCODE_POSITION_CLOSED";
      default:    return "TRADE_RETCODE_UNKNOWN";
   }
}

bool LoadTicketFromInbox(const string file_name,BridgeTicket &ticket,string &error_text)
{
   ticket.ticket_id = "";
   ticket.created_at = "";
   ticket.mode = "";
   ticket.symbol = "";
   ticket.side = "";
   ticket.order_plan = "";
   ticket.entry_count = 0;
   for(int i = 0; i < MAX_TICKET_ENTRIES; i++)
   {
      ticket.entry_types[i] = "";
      ticket.entry_prices[i] = 0.0;
      ticket.volume_lots[i] = 0.0;
      ticket.client_entry_ids[i] = "";
   }
   ticket.stop_loss = 0.0;
   ticket.take_profit = 0.0;
   ticket.trailing_enabled = false;
   ticket.trailing_activation_price = 0.0;
   ticket.trailing_distance_price = 0.0;
   ticket.trailing_step_price = 0.0;
   ticket.trailing_distance_mode = "";
   ticket.trailing_distance_value = 0.0;
   ticket.trailing_atr_period = 14;
   ticket.trailing_atr_timeframe = "H1";
   ticket.max_risk_usdt = 0.0;
   ticket.note = "";
   ticket.raw_json = "";
   ticket.file_name = file_name;

   const string path = BridgeFile("inbox",file_name);
   if(!ReadTextFile(path,ticket.raw_json))
   {
      error_text = "Could not read ticket file: " + path;
      return false;
   }

   if(!JsonGetString(ticket.raw_json,"ticket_id",ticket.ticket_id))
   {
      error_text = "Missing ticket_id";
      return false;
   }
   JsonGetString(ticket.raw_json,"created_at",ticket.created_at);
   if(!JsonGetString(ticket.raw_json,"mode",ticket.mode))
   {
      error_text = "Missing mode";
      return false;
   }
   if(!JsonGetString(ticket.raw_json,"symbol",ticket.symbol))
   {
      error_text = "Missing symbol";
      return false;
   }
   if(!JsonGetString(ticket.raw_json,"side",ticket.side))
   {
      error_text = "Missing side";
      return false;
   }
   if(!JsonGetString(ticket.raw_json,"order_plan",ticket.order_plan))
   {
      error_text = "Missing order_plan";
      return false;
   }

   string entries_json = "";
   if(!JsonGetArray(ticket.raw_json,"entries",entries_json))
   {
      error_text = "Missing entries array";
      return false;
   }

   const int entry_count = JsonCountTopLevelObjectsInArray(entries_json);
   if(entry_count <= 0)
   {
      error_text = "entries array must contain at least one entry object";
      return false;
   }
   if(entry_count > MAX_TICKET_ENTRIES)
   {
      error_text = "entries array exceeds MAX_TICKET_ENTRIES";
      return false;
   }
   ticket.entry_count = entry_count;

   for(int idx = 0; idx < ticket.entry_count; idx++)
   {
      string entry_json = "";
      if(!JsonGetObjectFromArrayAtIndex(entries_json,idx,entry_json))
      {
         error_text = "Could not parse entry object at index " + IntegerToString(idx);
         return false;
      }
      if(!JsonGetString(entry_json,"client_entry_id",ticket.client_entry_ids[idx]))
      {
         error_text = "Missing entries[" + IntegerToString(idx) + "].client_entry_id";
         return false;
      }
      if(!JsonGetString(entry_json,"entry_type",ticket.entry_types[idx]))
      {
         error_text = "Missing entries[" + IntegerToString(idx) + "].entry_type";
         return false;
      }
      if(ticket.entry_types[idx] != "market" && !JsonGetNumber(entry_json,"price",ticket.entry_prices[idx]))
      {
         error_text = "Missing entries[" + IntegerToString(idx) + "].price";
         return false;
      }
      if(!JsonGetNumber(entry_json,"volume_lots",ticket.volume_lots[idx]))
      {
         error_text = "Missing entries[" + IntegerToString(idx) + "].volume_lots";
         return false;
      }
   }

   string sl_json = "";
   if(!JsonGetObject(ticket.raw_json,"stop_loss",sl_json) || !JsonGetNumber(sl_json,"price",ticket.stop_loss))
   {
      error_text = "Missing stop_loss.price";
      return false;
   }

   string tp_json = "";
   if(!JsonGetObject(ticket.raw_json,"take_profit",tp_json) || !JsonGetNumber(tp_json,"price",ticket.take_profit))
   {
      error_text = "Missing take_profit.price";
      return false;
   }

   string trailing_json = "";
   if(JsonGetObject(ticket.raw_json,"trailing",trailing_json))
   {
      JsonGetBool(trailing_json,"enabled",ticket.trailing_enabled);
      if(!JsonGetNumber(trailing_json,"trigger_price",ticket.trailing_activation_price))
         JsonGetNumber(trailing_json,"activation_price",ticket.trailing_activation_price);
      if(!JsonGetNumber(trailing_json,"distance_value",ticket.trailing_distance_value))
      {
         if(JsonGetNumber(trailing_json,"distance_price",ticket.trailing_distance_price))
            ticket.trailing_distance_value = ticket.trailing_distance_price;
      }
      else
      {
         ticket.trailing_distance_price = ticket.trailing_distance_value;
      }
      JsonGetNumber(trailing_json,"step_price",ticket.trailing_step_price);
      JsonGetString(trailing_json,"distance_mode",ticket.trailing_distance_mode);
      if(ticket.trailing_distance_mode == "" && ticket.trailing_distance_value > 0.0)
         ticket.trailing_distance_mode = "price";

      double trailing_atr_period = 0.0;
      if(JsonGetNumber(trailing_json,"atr_period",trailing_atr_period) && trailing_atr_period > 0.0)
         ticket.trailing_atr_period = (int)MathRound(trailing_atr_period);
      JsonGetString(trailing_json,"atr_timeframe",ticket.trailing_atr_timeframe);
      if(ticket.trailing_atr_timeframe == "")
         ticket.trailing_atr_timeframe = "H1";
   }
   JsonGetNumber(ticket.raw_json,"max_risk_usdt",ticket.max_risk_usdt);
   JsonGetString(ticket.raw_json,"note",ticket.note);

   return true;
}

bool ValidateTicket(const BridgeTicket &ticket,string &error_text)
{
   if(InpPaperOnly && ticket.mode != "paper")
   {
      error_text = "Bridge is paper-only. Refusing non-paper mode.";
      return false;
   }

   if(ticket.order_plan == "market")
   {
      error_text = "v1 scaffold does not execute market tickets yet; pending orders only.";
      return false;
   }

   if(ticket.side != "buy" && ticket.side != "sell")
   {
      error_text = "side must be buy or sell";
      return false;
   }

   if(ticket.entry_count <= 0)
   {
      error_text = "Ticket must contain at least one entry";
      return false;
   }

   if(!SymbolSelect(ticket.symbol,true))
   {
      error_text = "SymbolSelect failed for symbol: " + ticket.symbol;
      return false;
   }

   if(ticket.stop_loss <= 0.0 || ticket.take_profit <= 0.0)
   {
      error_text = "SL and TP must both be > 0";
      return false;
   }

   bool has_limit = false;
   bool has_stop = false;
   for(int idx = 0; idx < ticket.entry_count; idx++)
   {
      const string entry_type = ticket.entry_types[idx];
      const double entry_price = ticket.entry_prices[idx];
      const double volume_lots = ticket.volume_lots[idx];
      if(volume_lots <= 0.0)
      {
         error_text = "entries[" + IntegerToString(idx) + "].volume_lots must be > 0";
         return false;
      }
      if(entry_type != "limit" && entry_type != "stop")
      {
         error_text = "Only limit and stop entries are supported in the pending-order bridge";
         return false;
      }
      if(entry_price <= 0.0)
      {
         error_text = "entries[" + IntegerToString(idx) + "].price must be > 0";
         return false;
      }
      if(entry_type == "limit") has_limit = true;
      if(entry_type == "stop") has_stop = true;

      if(ticket.side == "buy")
      {
         if(ticket.stop_loss >= entry_price)
         {
            error_text = "Buy ticket stop_loss must be below every entry price";
            return false;
         }
         if(ticket.take_profit <= entry_price)
         {
            error_text = "Buy ticket take_profit must be above every entry price";
            return false;
         }
      }
      else
      {
         if(ticket.stop_loss <= entry_price)
         {
            error_text = "Sell ticket stop_loss must be above every entry price";
            return false;
         }
         if(ticket.take_profit >= entry_price)
         {
            error_text = "Sell ticket take_profit must be below every entry price";
            return false;
         }
      }
   }

   if(ticket.order_plan == "limit_ladder" && !has_limit)
   {
      error_text = "limit_ladder requires at least one limit entry";
      return false;
   }
   if(ticket.order_plan == "stop_entry" && !has_stop)
   {
      error_text = "stop_entry requires at least one stop entry";
      return false;
   }
   if(ticket.order_plan == "hybrid_ladder_breakout")
   {
      if(ticket.entry_count < 2 || !has_limit || !has_stop)
      {
         error_text = "hybrid_ladder_breakout requires mixed limit + stop entries";
         return false;
      }
   }

   MqlTick tick;
   if(!SymbolInfoTick(ticket.symbol,tick))
   {
      error_text = "SymbolInfoTick failed for symbol: " + ticket.symbol;
      return false;
   }

   for(int idx2 = 0; idx2 < ticket.entry_count; idx2++)
   {
      const string entry_type2 = ticket.entry_types[idx2];
      const double entry_price2 = ticket.entry_prices[idx2];
      if(entry_type2 == "limit")
      {
         if(ticket.side == "buy" && entry_price2 >= tick.ask)
         {
            error_text = "Buy limit entry must be below current ask";
            return false;
         }
         if(ticket.side == "sell" && entry_price2 <= tick.bid)
         {
            error_text = "Sell limit entry must be above current bid";
            return false;
         }
      }
      else if(entry_type2 == "stop")
      {
         if(ticket.side == "buy" && entry_price2 <= tick.ask)
         {
            error_text = "Buy stop entry must be above current ask";
            return false;
         }
         if(ticket.side == "sell" && entry_price2 >= tick.bid)
         {
            error_text = "Sell stop entry must be below current bid";
            return false;
         }
      }
   }

   if(ticket.trailing_enabled)
   {
      const string trailing_mode = NormalizeMode(ticket.trailing_distance_mode);
      if(ticket.trailing_activation_price <= 0.0)
      {
         error_text = "Trailing requires trigger_price/activation_price > 0";
         return false;
      }
      if(trailing_mode != "price" && trailing_mode != "percent" && trailing_mode != "atr")
      {
         error_text = "Trailing distance_mode must be one of price, percent, atr";
         return false;
      }
      if(ticket.trailing_distance_value <= 0.0)
      {
         error_text = "Trailing requires distance_value > 0";
         return false;
      }
      if(ticket.trailing_step_price < 0.0)
      {
         error_text = "Trailing step_price must be >= 0";
         return false;
      }
      if(trailing_mode == "atr")
      {
         if(ticket.trailing_atr_period <= 0)
         {
            error_text = "Trailing ATR mode requires atr_period > 0";
            return false;
         }
         if(ParseTimeframeText(ticket.trailing_atr_timeframe) == PERIOD_CURRENT)
         {
            error_text = "Trailing ATR mode requires a valid atr_timeframe (e.g. M5, H1, H4, D1)";
            return false;
         }
      }
   }

   return true;
}

string BuildResultJson(const BridgeTicket &ticket,
                       const string status,
                       const string message,
                       const string archive_file,
                       const string error_file,
                       const double &normalized_entries[],
                       const double &normalized_volumes[],
                       const int normalized_count,
                       const double normalized_sl,
                       const double normalized_tp,
                       const ulong &order_ids[],
                       const int order_count,
                       const uint retcode,
                       const string retcode_text)
{
   const int digits = SymbolDigitsFor(ticket.symbol);
   string order_ids_json = "[";
   for(int i = 0; i < order_count; i++)
   {
      if(i > 0)
         order_ids_json += ", ";
      order_ids_json += ULongText(order_ids[i]);
   }
   order_ids_json += "]";

   string entries_json = "[";
   for(int j = 0; j < normalized_count; j++)
   {
      if(j > 0)
         entries_json += ", ";
      entries_json += "{\"client_entry_id\":\"" + JsonEscape(ticket.client_entry_ids[j]) + "\",";
      entries_json += "\"entry_type\":\"" + JsonEscape(ticket.entry_types[j]) + "\",";
      entries_json += "\"price\":" + DoubleToString(normalized_entries[j],digits) + ",";
      entries_json += "\"volume_lots\":" + DoubleToString(normalized_volumes[j],2) + "}";
   }
   entries_json += "]";

   const double first_entry = (normalized_count > 0 ? normalized_entries[0] : 0.0);
   const double first_volume = (normalized_count > 0 ? normalized_volumes[0] : 0.0);

   string json = "{";
   json += "\n  \"bridge_version\": \"mt5.paper.v1\",";
   json += "\n  \"ticket_id\": \"" + JsonEscape(ticket.ticket_id) + "\",";
   json += "\n  \"status\": \"" + JsonEscape(status) + "\",";
   json += "\n  \"symbol\": \"" + JsonEscape(ticket.symbol) + "\",";
   json += "\n  \"side\": \"" + JsonEscape(ticket.side) + "\",";
   json += "\n  \"order_plan\": \"" + JsonEscape(ticket.order_plan) + "\",";
   json += "\n  \"executor_mode\": \"paper\",";
   json += "\n  \"ticket_file\": \"" + JsonEscape(BridgeFile("inbox",ticket.file_name)) + "\",";
   json += "\n  \"archive_file\": " + (archive_file == "" ? "null" : "\"" + JsonEscape(archive_file) + "\"") + ",";
   json += "\n  \"error_file\": " + (error_file == "" ? "null" : "\"" + JsonEscape(error_file) + "\"") + ",";
   json += "\n  \"normalized_entry\": " + DoubleToString(first_entry,digits) + ",";
   json += "\n  \"normalized_volume_lots\": " + DoubleToString(first_volume,2) + ",";
   json += "\n  \"normalized_entries\": " + entries_json + ",";
   json += "\n  \"normalized_stop_loss\": " + DoubleToString(normalized_sl,digits) + ",";
   json += "\n  \"normalized_take_profit\": " + DoubleToString(normalized_tp,digits) + ",";
   json += "\n  \"mt5_order_ids\": " + order_ids_json + ",";
   json += "\n  \"mt5_position_ids\": [],";
   json += "\n  \"retcode\": " + IntegerToString((int)retcode) + ",";
   json += "\n  \"retcode_text\": \"" + JsonEscape(retcode_text) + "\",";
   json += "\n  \"message\": \"" + JsonEscape(message) + "\",";
   json += "\n  \"timestamp\": \"" + NowIso() + "\",";
   json += "\n  \"account\": {";
   json += "\n    \"login\": " + LongText(AccountInfoInteger(ACCOUNT_LOGIN)) + ",";
   json += "\n    \"server\": \"" + JsonEscape(AccountInfoString(ACCOUNT_SERVER)) + "\",";
   json += "\n    \"account_trade_allowed\": " + (AccountInfoInteger(ACCOUNT_TRADE_ALLOWED) != 0 ? "true" : "false") + ",";
   json += "\n    \"terminal_trade_allowed\": " + (TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) != 0 ? "true" : "false") + ",";
   json += "\n    \"mql_trade_allowed\": " + (MQLInfoInteger(MQL_TRADE_ALLOWED) != 0 ? "true" : "false");
   json += "\n  },";
   json += "\n  \"trailing\": {";
   json += "\n    \"enabled\": " + JsonBool(ticket.trailing_enabled) + ",";
   json += "\n    \"trigger_price\": " + JsonDoubleOrNull(ticket.trailing_activation_price,digits) + ",";
   json += "\n    \"distance_mode\": " + (ticket.trailing_distance_mode == "" ? "null" : "\"" + JsonEscape(NormalizeMode(ticket.trailing_distance_mode)) + "\"") + ",";
   json += "\n    \"distance_value\": " + JsonDoubleOrNull(ticket.trailing_distance_value,8) + ",";
   json += "\n    \"step_price\": " + JsonDoubleOrNull(ticket.trailing_step_price,digits) + ",";
   json += "\n    \"atr_period\": " + IntegerToString(ticket.trailing_atr_period) + ",";
   json += "\n    \"atr_timeframe\": \"" + JsonEscape(ticket.trailing_atr_timeframe) + "\",";
   json += "\n    \"mode\": \"ea_managed_v2\"";
   json += "\n  }";
   json += "\n}";
   return json;
}

bool WriteResultFile(const BridgeTicket &ticket,
                     const string status,
                     const string message,
                     const string archive_file,
                     const string error_file,
                     const double &normalized_entries[],
                     const double &normalized_volumes[],
                     const int normalized_count,
                     const double normalized_sl,
                     const double normalized_tp,
                     const ulong &order_ids[],
                     const int order_count,
                     const uint retcode,
                     const string retcode_text)
{
   const string result_name = FileSafeStamp() + "__" + ticket.ticket_id + "__result.json";
   const string result_path = BridgeFile("outbox",result_name);
   const string json = BuildResultJson(ticket,status,message,archive_file,error_file,normalized_entries,normalized_volumes,normalized_count,normalized_sl,normalized_tp,order_ids,order_count,retcode,retcode_text);
   return WriteTextFile(result_path,json);
}

bool CancelPendingOrderByTicket(const ulong order_ticket)
{
   if(order_ticket == 0 || !OrderSelect(order_ticket))
      return true;

   MqlTradeRequest req;
   MqlTradeResult res;
   ZeroMemory(req);
   ZeroMemory(res);
   req.action = TRADE_ACTION_REMOVE;
   req.order = order_ticket;
   req.symbol = OrderGetString(ORDER_SYMBOL);
   return OrderSend(req,res);
}

bool ExecuteTicket(const BridgeTicket &ticket,
                   double &normalized_entries[],
                   double &normalized_volumes[],
                   int &normalized_count,
                   double &normalized_sl,
                   double &normalized_tp,
                   ulong &order_ids[],
                   int &order_count,
                   uint &retcode,
                   string &retcode_text,
                   string &message)
{
   normalized_count = 0;
   order_count = 0;
   if(!NormalizePrice(ticket.symbol,ticket.stop_loss,normalized_sl) ||
      !NormalizePrice(ticket.symbol,ticket.take_profit,normalized_tp))
   {
      message = "Normalization failed for SL/TP fields";
      retcode = 10013;
      retcode_text = TradeRetcodeText(retcode);
      return false;
   }

   for(int idx = 0; idx < ticket.entry_count; idx++)
   {
      if(!NormalizePrice(ticket.symbol,ticket.entry_prices[idx],normalized_entries[idx]) ||
         !NormalizeVolume(ticket.symbol,ticket.volume_lots[idx],normalized_volumes[idx]))
      {
         message = "Normalization failed for entry index " + IntegerToString(idx);
         retcode = 10013;
         retcode_text = TradeRetcodeText(retcode);
         return false;
      }
      normalized_count++;
   }

   for(int j = 0; j < ticket.entry_count; j++)
   {
      MqlTradeRequest req;
      MqlTradeResult  res;
      ZeroMemory(req);
      ZeroMemory(res);

      req.action       = TRADE_ACTION_PENDING;
      req.symbol       = ticket.symbol;
      req.magic        = InpMagicNumber;
      req.volume       = normalized_volumes[j];
      req.price        = normalized_entries[j];
      req.sl           = normalized_sl;
      req.tp           = normalized_tp;
      req.deviation    = 20;
      req.type_time    = ORDER_TIME_GTC;
      req.type_filling = ORDER_FILLING_RETURN;
      req.comment      = ticket.ticket_id;

      if(ticket.entry_types[j] == "limit")
      {
         req.type = (ticket.side == "buy") ? ORDER_TYPE_BUY_LIMIT : ORDER_TYPE_SELL_LIMIT;
      }
      else if(ticket.entry_types[j] == "stop")
      {
         req.type = (ticket.side == "buy") ? ORDER_TYPE_BUY_STOP : ORDER_TYPE_SELL_STOP;
      }
      else
      {
         message = "Unsupported entry_type in ExecuteTicket";
         retcode = 10013;
         retcode_text = TradeRetcodeText(retcode);
         return false;
      }

      const bool ok = OrderSend(req,res);
      retcode = (uint)res.retcode;
      retcode_text = TradeRetcodeText(retcode);
      if(!(ok && (retcode == 10008 || retcode == 10009 || retcode == 10010)))
      {
         for(int rollback = 0; rollback < order_count; rollback++)
            CancelPendingOrderByTicket(order_ids[rollback]);
         order_count = 0;
         message = "Trade request failed at entry index " + IntegerToString(j) + ": " + res.comment;
         return false;
      }

      order_ids[order_count] = res.order;
      order_count++;
   }

   message = (order_count > 1)
             ? "Pending order package accepted by GrayPaperBridgeEA"
             : "Pending order accepted by GrayPaperBridgeEA";
   return true;
}

TrailingConfig BuildTrailingConfig(const BridgeTicket &ticket,const ulong order_id)
{
   TrailingConfig cfg;
   cfg.ticket_id = ticket.ticket_id;
   cfg.symbol = ticket.symbol;
   cfg.side = ticket.side;
   cfg.order_id = order_id;
   cfg.enabled = ticket.trailing_enabled;
   cfg.trigger_price = ticket.trailing_activation_price;
   cfg.distance_mode = NormalizeMode(ticket.trailing_distance_mode);
   cfg.distance_value = ticket.trailing_distance_value;
   cfg.step_price = ticket.trailing_step_price;
   cfg.atr_period = ticket.trailing_atr_period;
   cfg.atr_timeframe = ticket.trailing_atr_timeframe;
   return cfg;
}

string BuildTrailingConfigJson(const TrailingConfig &cfg)
{
   string json = "{";
   json += "\n  \"ticket_id\": \"" + JsonEscape(cfg.ticket_id) + "\",";
   json += "\n  \"symbol\": \"" + JsonEscape(cfg.symbol) + "\",";
   json += "\n  \"side\": \"" + JsonEscape(cfg.side) + "\",";
   json += "\n  \"order_id\": " + ULongText(cfg.order_id) + ",";
   json += "\n  \"enabled\": " + JsonBool(cfg.enabled) + ",";
   json += "\n  \"trigger_price\": " + JsonDoubleOrNull(cfg.trigger_price,SymbolDigitsFor(cfg.symbol)) + ",";
   json += "\n  \"distance_mode\": \"" + JsonEscape(cfg.distance_mode) + "\",";
   json += "\n  \"distance_value\": " + JsonDoubleOrNull(cfg.distance_value,8) + ",";
   json += "\n  \"step_price\": " + JsonDoubleOrNull(cfg.step_price,SymbolDigitsFor(cfg.symbol)) + ",";
   json += "\n  \"atr_period\": " + IntegerToString(cfg.atr_period) + ",";
   json += "\n  \"atr_timeframe\": \"" + JsonEscape(cfg.atr_timeframe) + "\"";
   json += "\n}";
   return json;
}

bool SaveTrailingConfig(const BridgeTicket &ticket,const ulong order_id)
{
   if(!ticket.trailing_enabled || order_id == 0)
      return true;

   const TrailingConfig cfg = BuildTrailingConfig(ticket,order_id);
   return WriteTextFile(BridgeFile("trailing",TrailingConfigFileName(ticket.ticket_id)),BuildTrailingConfigJson(cfg));
}

string BuildOrderIdsCsv(const ulong &order_ids[],const int order_count)
{
   string csv = "";
   for(int i = 0; i < order_count; i++)
   {
      if(i > 0)
         csv += ",";
      csv += ULongText(order_ids[i]);
   }
   return csv;
}

void ParseOrderIdsCsv(const string csv,ulong &order_ids[],int &order_count)
{
   order_count = 0;
   const int len = StringLen(csv);
   string token = "";
   for(int i = 0; i <= len; i++)
   {
      const bool at_end = (i == len);
      const int ch = at_end ? ',' : StringGetCharacter(csv,i);
      if(ch == ',')
      {
         StringTrimLeft(token);
         StringTrimRight(token);
         if(token != "" && order_count < MAX_TICKET_ENTRIES)
         {
            order_ids[order_count] = (ulong)StringToInteger(token);
            order_count++;
         }
         token = "";
      }
      else
         token += StringSubstr(csv,i,1);
   }
}

string BuildPackageConfigJson(const PackageConfig &cfg)
{
   string json = "{";
   json += "\n  \"ticket_id\": \"" + JsonEscape(cfg.ticket_id) + "\",";
   json += "\n  \"symbol\": \"" + JsonEscape(cfg.symbol) + "\",";
   json += "\n  \"side\": \"" + JsonEscape(cfg.side) + "\",";
   json += "\n  \"order_plan\": \"" + JsonEscape(cfg.order_plan) + "\",";
   json += "\n  \"cancel_other_on_fill\": " + JsonBool(cfg.cancel_other_on_fill) + ",";
   json += "\n  \"order_ids_csv\": \"" + JsonEscape(BuildOrderIdsCsv(cfg.order_ids,cfg.order_count)) + "\"";
   json += "\n}";
   return json;
}

bool SavePackageConfig(const BridgeTicket &ticket,const ulong &order_ids[],const int order_count)
{
   if(ticket.order_plan != "hybrid_ladder_breakout" || order_count <= 0)
      return true;

   PackageConfig cfg;
   cfg.ticket_id = ticket.ticket_id;
   cfg.symbol = ticket.symbol;
   cfg.side = ticket.side;
   cfg.order_plan = ticket.order_plan;
   cfg.cancel_other_on_fill = true;
   cfg.order_count = order_count;
   for(int i = 0; i < MAX_TICKET_ENTRIES; i++)
      cfg.order_ids[i] = (i < order_count ? order_ids[i] : 0);
   return WriteTextFile(BridgeFile("trailing",PackageConfigFileName(ticket.ticket_id)),BuildPackageConfigJson(cfg));
}

bool LoadPackageConfig(const string file_name,PackageConfig &cfg,string &error_text)
{
   string raw = "";
   if(!ReadTextFile(BridgeFile("trailing",file_name),raw))
   {
      error_text = "Could not read package config file";
      return false;
   }

   cfg.ticket_id = "";
   cfg.symbol = "";
   cfg.side = "";
   cfg.order_plan = "";
   cfg.cancel_other_on_fill = false;
   cfg.order_count = 0;
   for(int i = 0; i < MAX_TICKET_ENTRIES; i++)
      cfg.order_ids[i] = 0;

   if(!JsonGetString(raw,"ticket_id",cfg.ticket_id) || !JsonGetString(raw,"symbol",cfg.symbol) || !JsonGetString(raw,"side",cfg.side))
   {
      error_text = "Package config missing core fields";
      return false;
   }
   JsonGetString(raw,"order_plan",cfg.order_plan);
   JsonGetBool(raw,"cancel_other_on_fill",cfg.cancel_other_on_fill);
   string csv = "";
   JsonGetString(raw,"order_ids_csv",csv);
   ParseOrderIdsCsv(csv,cfg.order_ids,cfg.order_count);
   return true;
}

bool ArchivePackageConfigFile(const string file_name)
{
   string raw = "";
   if(!ReadTextFile(BridgeFile("trailing",file_name),raw))
      return false;

   const string archive_path = BridgeFile("trailing_archive",FileSafeStamp() + "__" + file_name);
   if(!WriteTextFile(archive_path,raw))
      return false;
   return FileDelete(BridgeFile("trailing",file_name));
}

bool LoadTrailingConfig(const string file_name,TrailingConfig &cfg,string &error_text)
{
   string raw = "";
   if(!ReadTextFile(BridgeFile("trailing",file_name),raw))
   {
      error_text = "Could not read trailing config file";
      return false;
   }

   cfg.ticket_id = "";
   cfg.symbol = "";
   cfg.side = "";
   cfg.order_id = 0;
   cfg.enabled = false;
   cfg.trigger_price = 0.0;
   cfg.distance_mode = "";
   cfg.distance_value = 0.0;
   cfg.step_price = 0.0;
   cfg.atr_period = 14;
   cfg.atr_timeframe = "H1";

   if(!JsonGetString(raw,"ticket_id",cfg.ticket_id))
   {
      error_text = "Trailing config missing ticket_id";
      return false;
   }
   if(!JsonGetString(raw,"symbol",cfg.symbol))
   {
      error_text = "Trailing config missing symbol";
      return false;
   }
   if(!JsonGetString(raw,"side",cfg.side))
   {
      error_text = "Trailing config missing side";
      return false;
   }
   double order_id_value = 0.0;
   if(JsonGetNumber(raw,"order_id",order_id_value) && order_id_value > 0.0)
      cfg.order_id = (ulong)MathRound(order_id_value);
   JsonGetBool(raw,"enabled",cfg.enabled);
   JsonGetNumber(raw,"trigger_price",cfg.trigger_price);
   JsonGetString(raw,"distance_mode",cfg.distance_mode);
   JsonGetNumber(raw,"distance_value",cfg.distance_value);
   JsonGetNumber(raw,"step_price",cfg.step_price);
   double atr_period_value = 0.0;
   if(JsonGetNumber(raw,"atr_period",atr_period_value) && atr_period_value > 0.0)
      cfg.atr_period = (int)MathRound(atr_period_value);
   JsonGetString(raw,"atr_timeframe",cfg.atr_timeframe);
   return true;
}

bool ArchiveTrailingConfigFile(const string file_name)
{
   string raw = "";
   if(!ReadTextFile(BridgeFile("trailing",file_name),raw))
      return false;

   const string archive_path = BridgeFile("trailing_archive",FileSafeStamp() + "__" + file_name);
   if(!WriteTextFile(archive_path,raw))
      return false;
   return FileDelete(BridgeFile("trailing",file_name));
}

bool FindManagedPosition(const TrailingConfig &cfg,
                         ulong &position_ticket,
                         double &current_sl,
                         double &current_tp,
                         long &position_type)
{
   position_ticket = 0;
   current_sl = 0.0;
   current_tp = 0.0;
   position_type = -1;

   ulong fallback_ticket = 0;
   double fallback_sl = 0.0;
   double fallback_tp = 0.0;
   long fallback_type = -1;
   int fallback_count = 0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      const ulong pos_ticket = PositionGetTicket(i);
      if(pos_ticket == 0 || !PositionSelectByTicket(pos_ticket))
         continue;

      if(PositionGetString(POSITION_SYMBOL) != cfg.symbol)
         continue;
      if(PositionGetInteger(POSITION_MAGIC) != (long)InpMagicNumber)
         continue;

      const long pos_type = PositionGetInteger(POSITION_TYPE);
      if(cfg.side == "buy" && pos_type != POSITION_TYPE_BUY)
         continue;
      if(cfg.side == "sell" && pos_type != POSITION_TYPE_SELL)
         continue;

      const string comment = PositionGetString(POSITION_COMMENT);
      if(comment == cfg.ticket_id)
      {
         position_ticket = pos_ticket;
         current_sl = PositionGetDouble(POSITION_SL);
         current_tp = PositionGetDouble(POSITION_TP);
         position_type = pos_type;
         return true;
      }

      fallback_ticket = pos_ticket;
      fallback_sl = PositionGetDouble(POSITION_SL);
      fallback_tp = PositionGetDouble(POSITION_TP);
      fallback_type = pos_type;
      fallback_count++;
   }

   if(fallback_count == 1)
   {
      position_ticket = fallback_ticket;
      current_sl = fallback_sl;
      current_tp = fallback_tp;
      position_type = fallback_type;
      return true;
   }

   return false;
}

bool ResolveTrailingDistance(const TrailingConfig &cfg,const double current_price,double &distance,string &error_text)
{
   error_text = "";
   const string mode = NormalizeMode(cfg.distance_mode);

   if(mode == "price")
   {
      distance = cfg.distance_value;
      return (distance > 0.0);
   }

   if(mode == "percent")
   {
      distance = current_price * cfg.distance_value / 100.0;
      return (distance > 0.0);
   }

   if(mode == "atr")
   {
      const int timeframe = ParseTimeframeText(cfg.atr_timeframe);
      if(timeframe == PERIOD_CURRENT)
      {
         error_text = "Trailing ATR timeframe is invalid";
         return false;
      }

      const int handle = iATR(cfg.symbol,(ENUM_TIMEFRAMES)timeframe,cfg.atr_period);
      if(handle == INVALID_HANDLE)
      {
         error_text = "Could not create ATR handle";
         return false;
      }

      double buffer[];
      ArraySetAsSeries(buffer,true);
      const int copied = CopyBuffer(handle,0,0,1,buffer);
      IndicatorRelease(handle);
      if(copied <= 0 || !MathIsValidNumber(buffer[0]) || buffer[0] <= 0.0)
      {
         error_text = "Could not read ATR value";
         return false;
      }

      distance = buffer[0] * cfg.distance_value;
      return (distance > 0.0);
   }

   error_text = "Unsupported trailing distance mode";
   return false;
}

bool ApplyTrailingForConfig(const TrailingConfig &cfg,string &message)
{
   message = "";
   if(!cfg.enabled)
      return false;

   ulong position_ticket = 0;
   double current_sl = 0.0;
   double current_tp = 0.0;
   long position_type = -1;
   const bool has_position = FindManagedPosition(cfg,position_ticket,current_sl,current_tp,position_type);
   if(!has_position)
   {
      if(cfg.order_id > 0 && OrderSelect(cfg.order_id))
         return false;
      return false;
   }

   MqlTick tick;
   if(!SymbolInfoTick(cfg.symbol,tick))
   {
      message = "Trailing skipped: SymbolInfoTick failed for " + cfg.symbol;
      return false;
   }

   const double current_price = (cfg.side == "buy") ? tick.bid : tick.ask;
   if((cfg.side == "buy" && current_price < cfg.trigger_price) ||
      (cfg.side == "sell" && current_price > cfg.trigger_price))
      return false;

   double distance = 0.0;
   string error_text = "";
   if(!ResolveTrailingDistance(cfg,current_price,distance,error_text))
   {
      message = "Trailing skipped: " + error_text;
      return false;
   }

   double tick_size = SymbolInfoDouble(cfg.symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick_size <= 0.0)
      tick_size = SymbolInfoDouble(cfg.symbol,SYMBOL_POINT);
   const double point = SymbolInfoDouble(cfg.symbol,SYMBOL_POINT);
   const double min_step = (cfg.step_price > 0.0 ? cfg.step_price : tick_size);
   const double stop_gap = (double)SymbolInfoInteger(cfg.symbol,SYMBOL_TRADE_STOPS_LEVEL) * point;
   const double freeze_gap = (double)SymbolInfoInteger(cfg.symbol,SYMBOL_TRADE_FREEZE_LEVEL) * point;
   const double min_gap = MathMax(MathMax(stop_gap,freeze_gap),tick_size);

   double proposed_sl = 0.0;
   if(cfg.side == "buy")
   {
      proposed_sl = current_price - distance;
      const double max_allowed = current_price - min_gap;
      if(proposed_sl > max_allowed)
         proposed_sl = max_allowed;
   }
   else
   {
      proposed_sl = current_price + distance;
      const double min_allowed = current_price + min_gap;
      if(proposed_sl < min_allowed)
         proposed_sl = min_allowed;
   }

   if(!NormalizePrice(cfg.symbol,proposed_sl,proposed_sl) || proposed_sl <= 0.0)
      return false;

   if(cfg.side == "buy")
   {
      if(current_sl > 0.0 && proposed_sl <= current_sl + min_step)
         return false;
   }
   else
   {
      if(current_sl > 0.0 && proposed_sl >= current_sl - min_step)
         return false;
   }

   MqlTradeRequest req;
   MqlTradeResult res;
   ZeroMemory(req);
   ZeroMemory(res);

   req.action = TRADE_ACTION_SLTP;
   req.symbol = cfg.symbol;
   req.position = position_ticket;
   req.sl = proposed_sl;
   req.tp = current_tp;
   req.magic = InpMagicNumber;

   const bool ok = OrderSend(req,res);
   const uint retcode = (uint)res.retcode;
   if(ok && (retcode == 10008 || retcode == 10009 || retcode == 10010))
   {
      message = "Trailing updated for " + cfg.ticket_id + " -> SL=" + DoubleToString(proposed_sl,SymbolDigitsFor(cfg.symbol));
      return true;
   }

   message = "Trailing SLTP modify failed for " + cfg.ticket_id + ": " + res.comment;
   return false;
}

void ProcessTrailingConfigFile(const string file_name)
{
   if(StringFind(file_name,"__package.json") >= 0)
      return;

   TrailingConfig cfg;
   string error_text = "";
   if(!LoadTrailingConfig(file_name,cfg,error_text))
   {
      Print("GrayPaperBridgeEA trailing load failure: ",error_text);
      return;
   }

   string message = "";
   const bool changed = ApplyTrailingForConfig(cfg,message);
   if(changed && message != "")
      Print(message);

   if(!OrderSelect(cfg.order_id))
   {
      ulong position_ticket = 0;
      double current_sl = 0.0;
      double current_tp = 0.0;
      long position_type = -1;
      if(!FindManagedPosition(cfg,position_ticket,current_sl,current_tp,position_type) && !changed)
         ArchiveTrailingConfigFile(file_name);
   }
}

void ManageTrailingOnce()
{
   string file_name = "";
   long search_handle = FileFindFirst(BridgeFile("trailing","*.json"),file_name);
   if(search_handle == INVALID_HANDLE)
      return;

   ProcessTrailingConfigFile(file_name);
   while(FileFindNext(search_handle,file_name))
      ProcessTrailingConfigFile(file_name);
   FileFindClose(search_handle);
}

bool HasHybridPosition(const PackageConfig &cfg)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      const ulong pos_ticket = PositionGetTicket(i);
      if(pos_ticket == 0 || !PositionSelectByTicket(pos_ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL) != cfg.symbol)
         continue;
      if(PositionGetInteger(POSITION_MAGIC) != (long)InpMagicNumber)
         continue;
      const string comment = PositionGetString(POSITION_COMMENT);
      if(comment == cfg.ticket_id)
         return true;
   }
   return false;
}

void ProcessPackageConfigFile(const string file_name)
{
   if(StringFind(file_name,"__package.json") < 0)
      return;

   PackageConfig cfg;
   string error_text = "";
   if(!LoadPackageConfig(file_name,cfg,error_text))
   {
      Print("GrayPaperBridgeEA package load failure: ",error_text);
      return;
   }

   const bool has_position = HasHybridPosition(cfg);
   bool any_pending = false;
   for(int i = 0; i < cfg.order_count; i++)
   {
      const ulong order_ticket = cfg.order_ids[i];
      if(order_ticket == 0)
         continue;
      if(OrderSelect(order_ticket))
      {
         any_pending = true;
         if(has_position && cfg.cancel_other_on_fill)
            CancelPendingOrderByTicket(order_ticket);
      }
   }

   if(has_position && cfg.cancel_other_on_fill)
   {
      ArchivePackageConfigFile(file_name);
      return;
   }

   any_pending = false;
   for(int j = 0; j < cfg.order_count; j++)
   {
      if(cfg.order_ids[j] > 0 && OrderSelect(cfg.order_ids[j]))
      {
         any_pending = true;
         break;
      }
   }
   if(!any_pending)
      ArchivePackageConfigFile(file_name);
}

void ManagePackagesOnce()
{
   string file_name = "";
   long search_handle = FileFindFirst(BridgeFile("trailing","*__package.json"),file_name);
   if(search_handle == INVALID_HANDLE)
      return;

   ProcessPackageConfigFile(file_name);
   while(FileFindNext(search_handle,file_name))
      ProcessPackageConfigFile(file_name);
   FileFindClose(search_handle);
}

void ProcessTicketFile(const string file_name)
{
   BridgeTicket ticket;
   string error_text = "";

   if(!LoadTicketFromInbox(file_name,ticket,error_text))
   {
      Print("GrayPaperBridgeEA load failure: ",error_text);
      return;
   }

   double normalized_entries[MAX_TICKET_ENTRIES];
   double normalized_volumes[MAX_TICKET_ENTRIES];
   ArrayInitialize(normalized_entries,0.0);
   ArrayInitialize(normalized_volumes,0.0);
   int normalized_count = 0;
   double normalized_sl = 0.0;
   double normalized_tp = 0.0;
   ulong order_ids[MAX_TICKET_ENTRIES];
   ArrayInitialize(order_ids,0);
   int order_count = 0;
   uint retcode = 0;
   string retcode_text = "";
   string archive_file = "";
   string error_file = "";
   string message = "";

   if(!ValidateTicket(ticket,error_text))
   {
      retcode = 10013;
      retcode_text = TradeRetcodeText(retcode);
      message = error_text;
      CopyInboxFileTo("errors",ticket,error_file);
      WriteResultFile(ticket,"rejected",message,archive_file,error_file,normalized_entries,normalized_volumes,normalized_count,normalized_sl,normalized_tp,order_ids,order_count,retcode,retcode_text);
      DeleteInboxFile(ticket);
      Print("GrayPaperBridgeEA rejected ticket ",ticket.ticket_id,": ",message);
      return;
   }

   const bool executed = ExecuteTicket(ticket,normalized_entries,normalized_volumes,normalized_count,normalized_sl,normalized_tp,order_ids,order_count,retcode,retcode_text,message);

   if(executed)
   {
      CopyInboxFileTo("archive",ticket,archive_file);
      if(!SaveTrailingConfig(ticket,(order_count > 0 ? order_ids[0] : 0)))
         Print("GrayPaperBridgeEA warning: could not persist trailing config for ",ticket.ticket_id);
      if(!SavePackageConfig(ticket,order_ids,order_count))
         Print("GrayPaperBridgeEA warning: could not persist package config for ",ticket.ticket_id);
   }
   else
      CopyInboxFileTo("errors",ticket,error_file);

   WriteResultFile(ticket,executed ? "accepted" : "rejected",message,archive_file,error_file,normalized_entries,normalized_volumes,normalized_count,normalized_sl,normalized_tp,order_ids,order_count,retcode,retcode_text);
   DeleteInboxFile(ticket);

   string order_ids_text = "";
   for(int oi = 0; oi < order_count; oi++)
   {
      if(oi > 0)
         order_ids_text += ",";
      order_ids_text += ULongText(order_ids[oi]);
   }

   Print("GrayPaperBridgeEA processed ticket ",ticket.ticket_id,
         " status=",(executed ? "accepted" : "rejected"),
         " retcode=",IntegerToString((int)retcode),
         " order_ids=",order_ids_text);
}

void ProcessInboxOnce()
{
   string file_name = "";
   long search_handle = FileFindFirst(BridgeFile("inbox","*.json"),file_name);
   if(search_handle == INVALID_HANDLE)
      return;

   ProcessTicketFile(file_name);
   FileFindClose(search_handle);
}

int OnInit()
{
   EnsureBridgeFolders();
   EventSetTimer(MathMax(InpPollSeconds,1));
   Print("GrayPaperBridgeEA initialized. Watching ",BridgeDir("inbox"));
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   EventKillTimer();
}

void OnTick()
{
   // Execution is timer-driven so the EA can run quietly while attached to a chart.
}

void OnTimer()
{
   ProcessInboxOnce();
   ManageTrailingOnce();
   ManagePackagesOnce();
}
