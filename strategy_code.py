from QuantConnect import Resolution
from QuantConnect.Algorithm import QCAlgorithm


class NCAVsimple(QCAlgorithm):
    def Initialize(self):
        #rebalancing should occur in July
        self.SetStartDate(2000, 1, 1)
        self.SetCash(100000) 
        self.UniverseSettings.Resolution = Resolution.Daily
        self.filtered_fine = None
        self.filtered_coarse = None
        self.symbol = self.AddEquity('SPY', Resolution.Daily).Symbol

        self.coarse_count = 3000
        # self.SetSecurityInitializer(lambda x: x.SetMarketPrice(self.GetLastKnownPrice(x)))
        
        self.monthly_rebalance = False
        self.AddUniverse(self.CoarseSelectionFunction,self.FineSelectionFunction)
        self.Schedule.On(self.DateRules.MonthEnd(self.symbol), self.TimeRules.AfterMarketOpen(self.symbol), self.rebalance)
        
    def CoarseSelectionFunction(self, coarse):
        if self.monthly_rebalance:
            # drop stocks which have no fundamental data or have low price
            self.filtered_coarse = [x.Symbol for x in coarse if (x.HasFundamentalData) and x.Market == 'usa']
            return self.filtered_coarse
        else: 
            return Universe.Unchanged      
    
    def FineSelectionFunction(self, fine):
        if self.monthly_rebalance:
            fine = [x for x in fine if x.EarningReports.BasicAverageShares.ThreeMonths > 0 and x.MarketCap != 0 and x.ValuationRatios.WorkingCapitalPerShare != 0]
            sorted_by_market_cap = sorted(fine, key = lambda x:x.MarketCap, reverse=True)
            top_by_market_cap = [x for x in sorted_by_market_cap[:self.coarse_count]]
            
            #NCAV/MV Calc: (Current Assets - Total Liabs Reported)/ Market Cap
            self.filtered_fine = [x.Symbol for x in top_by_market_cap if ((x.FinancialStatements.BalanceSheet.CurrentAssets.TwelveMonths - x.FinancialStatements.BalanceSheet.TotalLiabilitiesAsReported.TwelveMonths) / x.MarketCap) > 1.5]

            return self.filtered_fine
        else:
            return []
    
    def rebalance(self):
        #quarterly rebalance
        if self.Time.month%3 == 0:
            self.Debug("Rebalance" + str(self.Time))
            self.monthly_rebalance = True
        
    def OnData(self, data):
        if not self.monthly_rebalance: return 

        stocks_invested = [x.Key for x in self.Portfolio if x.Value.Invested]
        for symbol in stocks_invested:
            # if the NCAV is no longer > 1.5 liquidate
            if symbol not in self.filtered_fine:
                self.Liquidate(symbol)

        for symbol in self.filtered_fine:
            if self.Securities[symbol].Price != 0 and self.Securities[symbol].IsTradable:  # Prevent error message.
                self.SetHoldings(symbol, 1 / len(self.filtered_fine))
