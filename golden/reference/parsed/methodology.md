<table>
  <tr>
    <td colspan="2">Bloomberg Versa Indices</td>
  </tr>
  <tr>
    <td colspan="2">Methodology</td>
  </tr>
</table>

March 21, 2025

## Bloomberg Versa Indices Methodology

## March 21, 2025

# Table of Contents

<table>
  <tr>
    <td>Introduction</td>
    <td>4</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Objectives and Key Features</td>
    <td>4</td>
  </tr>
  <tr>
    <td>Section 1: Calculation of the Volatility Target Index</td>
    <td>4</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Index Value Calculation</td>
    <td>4</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Exposure Calculation</td>
    <td>6</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Exposure Direction Calculation</td>
    <td>7</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Underlying Index Volatility Calculation</td>
    <td>8</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Signal Calculation</td>
    <td>10</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Glossary for Section 1</td>
    <td>11</td>
  </tr>
  <tr>
    <td>Section 2: Calculation of the Dynamic Treasury Volatility Target Index</td>
    <td>14</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Index Value Calculation</td>
    <td>14</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Units</td>
    <td>14</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Weights</td>
    <td>15</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Volatility</td>
    <td>15</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Exposure Direction</td>
    <td>16</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Signal Type</td>
    <td>16</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Funding Cost</td>
    <td>17</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Transaction Cost</td>
    <td>18</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Glossary for Section 2</td>
    <td>18</td>
  </tr>
  <tr>
    <td>Section 3: Calculation of the Multi-Asset Basket Index</td>
    <td>20</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Index Value Calculation</td>
    <td>20</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Units</td>
    <td>21</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Incremental Units</td>
    <td>21</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Adjustments</td>
    <td>22</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Weights</td>
    <td>22</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Multi-Asset Signal</td>
    <td>23</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Glossary for Section 3</td>
    <td>24</td>
  </tr>
  <tr>
    <td>Section 4: Backtest assumptions</td>
    <td>26</td>
  </tr>
  <tr>
    <td>Section 5: Stakeholder engagement, risk, and limitations</td>
    <td>26</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Limitations of the index</td>
    <td>26</td>
  </tr>
  <tr>
    <td>Section 6: Benchmark oversight and governance</td>
    <td>27</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Benchmark governance, audit, and review structure</td>
    <td>27</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Index and Methodology Changes</td>
    <td>27</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Expert judgement and Discretion</td>
    <td>27</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Conflicts of interest</td>
    <td>27</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Restatement policy</td>
    <td>27</td>
  </tr>
  <tr>
    <td>&nbsp;&nbsp;&nbsp;&nbsp;Cessation Policy</td>
    <td>27</td>
  </tr>
  <tr>
    <td>Appendix I: Glossary for All Sections</td>
    <td>28</td>
  </tr>
  <tr>
    <td>Appendix II: Market Disruptions</td>
    <td>29</td>
  </tr>
</table>

## Bloomberg Versa Indices Methodology

## March 21, 2025

Appendix III: Synthetic High/Lows Levels

Appendix IV: ESG Disclosures

Bloomberg Versa Indices Methodology

3

## Bloomberg Versa Indices Methodology

## March 21, 2025

## Introduction

This methodology (the “Methodology”) has been made available by Bloomberg Index Services Limited (“BISL”) and sets out the rules, criteria, risk factors and other information applicable to the Bloomberg Versa Indices (the “Indices” and each, an “Index”). Capitalized terms used in this Methodology but not otherwise defined have the meanings set forth in the Glossary for each Section.

## Objectives and Key Features

The Bloomberg Versa Indices aim to reflect the performance of individual volatility-targeting indices, a multi-asset index composed of these indices, and a volatility-targeted version of such multi-asset index.

## Section 1: Calculation of the Volatility Target Index

## Index Value Calculation

With respect to the Index, the Index Value on the Index Base Date shall be the Index Base Value. Thereafter, the Index Value with respect to each Index Business Day, t, shall be calculated in accordance with the following formula. The Index Value shall be floored at zero on any Index Business Day. If the Index Value hits zero, it will stay at zero:

$$
I_t = \begin{cases} \max(I_{t-1} + R_t^U + R_t^C + R_{t-1}^{TC} + R_t^D, 0), & \text{if t is Index Base Date or } I_{t-1} \neq 0 \\ 0, & \text{if } I_{t-1} = 0 \end{cases} \tag{1}
$$

The Index returns are calculated in accordance with the following formula:

$$
R_t^U = Unit_{t-1}^U \times (I_t^U - I_{t-1}^U) \qquad (2)
$$

$$
R_t^C = Unit_{t-1}^C \times (I_t^C - I_{t-1}^C) \qquad (3)
$$

$$
R_t^{TC} = -abs(Unit_t^U - Unit_{t-1}^U) \times I_t^U \times TCR \quad (4)
$$

$$
R_t^D = -I_{t-1} \times DeductionFactor \times \frac{ACT_{t,t-1}}{DC} \qquad (5)
$$

The units of the Underlying Index and the Cash Index are calculated in accordance with the following formula:

$$
Unit_t^U = \begin{cases} \frac{AE_d \times I_t}{I_t^U}, & \text{if t is Index Base Date} \\ \frac{AE_d \times I_{t-InputPriceLag}}{I_{t-InputPriceLag}^U}, & \text{if t is a Rebalance Date, but not the Index Base Date} \\ Unit_{t-1}^U, & \text{else} \end{cases} \qquad (6)
$$

$$
Unit_t^C = \begin{cases} \frac{CE_d \times I_t}{I_t^C}, & \text{if t is Index Base Date} \\ \frac{CE_d \times I_{t-InputPriceLag}}{I_t^C}, & \text{if t is a Rebalance Date, but not Index Base Date} \\ Unit_{t-1}^C, & \text{else} \end{cases} \qquad (7)
$$

For each type of Volatility Target Index, the exposure to cash shall be determined in accordance with the following formula:

Bloomberg Versa Indices Methodology

4

## Bloomberg Versa Indices Methodology

## March 21, 2025

## Type I

It is assumed that no cash return or financing cost occurs in the volatility control process. The Index Value is Excess Return:

$$
CE_d = 0 \qquad (8)
$$

## Type II

It is assumed that cash returns are earned by 100% of the Index Value despite the change in the exposure of the Underlying Index. The Index Value is Total Return:

$$
CE_d = 1 \qquad (9)
$$

## Type III

It is assumed that financing costs occur on the exposure of the Underlying Index. The Index Value is Excess Return:

$$
CE_d = -AE_d \tag{10}
$$

## Type IV

It is assumed that:

a) If the exposure of the Underlying Index is less than 100%, cash returns will occur on part of the asset that is not invested.

b) If the exposure of the Underlying Index is more than 100%, financing costs will occur on part of the asset that is borrowed.

c) If the exposure of the Underlying Index is equal to 100%, there will be no cash return or financing cost.

The Index Value is Total Return:

$$
CE_d = 1 - AE_d \tag{11}
$$

Where:

$abs(x)$ means the absolute value of $x$;

$\max(a, b)$ means the maximum value of $a$ and $b$;

$d$ means the Determination Date;

$t$ means Index Business Day $t$;

$t-1$ means one Index Business Day immediately preceding Index Business Day $t$;

$ACT_{t,t-1}$ means the number of calendar days from, and excluding, Index Business Day $t-1$ to, and including, Index Business Day $t$;

$AE_d$ means Actual Exposure as of Determination Date $d$, referring to Section Exposure Calculation;

$CE_d$ means the exposure of the Cash Index on Determination Date $d$;

$CR_t$ means the cash rate of the Cash Index on Index Business Day $t$;

$DC$ means Day Count Convention;

$DeductionFactor$ means the Deduction Factor;

$I_t$ means the Index Value on Index Business Day $t$;

$I_{t-1}$ means the Index Value on Index Business Day $t-1$;

Bloomberg Versa Indices Methodology

5

## Bloomberg Versa Indices Methodology

## March 21, 2025

$I_t^C$ means the level of the Cash Index on Index Business Day $t$;

$I_t^U$ means the level of the Underlying Index on Index Business Day $t$;

*InputPriceLag* means the Input Price Lag;

$R_t^C$ means the return of the Cash Index on Index Business Day $t$;

$R_t^D$ means the deduction return on Index Business Day $t$, where $R_t^D = 0$ on Index Base Date;

$R_{t-1}^{TC}$ means the transaction cost on Index Business Day $t-1$, and $R_t^{TC} = 0$ on Index Base Date or the first Index Business Day immediately after Index Base Date;

$R_t^U$ means the return of the Underlying Index on Index Business Day $t$;

*TCR* means the Transaction Cost Rate;

$Unit_t^U$ means the units of the Underlying Index on Index Business Day $t$;

$Unit_t^C$ means the units of the Cash Index on Index Business Day $t$;

$Unit_{t-1}^U$ means the units of the Underlying Index on Index Business Day $t-1$;

$Unit_{t-1}^C$ means the units of the Cash Index on Index Business Day $t-1$;

## Exposure Calculation

With respect to the first Determination Date, the Actual Exposure for Index calculation is equal to the Target Exposure. Thereafter, the Actual Exposure with respect to each Determination Date, d, shall be calculated in accordance with the following formula:

If there is no threshold on exposure changes, on each Determination Date d:

$$
AE_d = TE_d \tag{12}
$$

If there is an absolute threshold of exposure changes, on each Determination Date d:

$$
AE_d = \begin{cases} TE_d, & \text{if } abs(TE_d - AE_{d-1}) \ge TH \\ AE_{d-1}, & \text{else} \end{cases} \tag{13}
$$

If there is a relative threshold of exposure changes, on each Determination Date d:

$$
AE_d = \begin{cases} TE_d, & \text{if } abs(TE_d - AE_{d-1}) \ge TH \times abs(AE_{d-1}) \\ AE_{d-1}, & \text{else} \end{cases} \qquad (14)
$$

Where:

$abs(x)$ means the absolute value of $x$;

$d$ means the Determination Date;

$d - 1$ means the Determination Date immediately preceding to Determination Date $d$;

$AE_d$ means Actual Exposure of the Underlying Index on Determination Date $d$;

$AE_{d-1}$ means Actual Exposure of the Underlying Index on Determination Date $d - 1$;

$TE_d$ means Target Exposure of the Underlying Index on Determination Date $d$ calculated as below:

If Target Exposure Type is Standard Target Exposure, which is the default option:

Bloomberg Versa Indices Methodology

6

## Bloomberg Versa Indices Methodology

## March 21, 2025

$$
TE_d = max\left(min\left(TE_{MAX}, \frac{VT}{V_d^U}\right), TE_{MIN}\right) \times Dir_{d-DirectionLag} \quad (15)
$$

If Target Exposure Type is Target Exposure with Risk Factor Scalar:

$$
TE_d = PremE_d \times \left(1 - max\left(1 - abs\left(\frac{TE_{MAX}}{PremE_d}\right), 0\right)\right) \quad (16)
$$

$$
\begin{aligned}
PremE_d = \max \left( \min \left( TE_{MAX}, \frac{VT}{V_d^U} \right), TE_{MIN} \right) \times Dir_{d-DirectionLag} \\
+ abs \left( \max \left( \min \left( TE_{MAX}, \frac{VT}{V_d^U} \right), TE_{MIN} \right) \times Dir_{d-DirectionLag} \right) \times (RiskFactorScalar_{d-DirectionLag} - 1)
\end{aligned} 
\quad (17)
$$

Where:

d – DirectionLag means the number of Direction Lag Index Business Days immediately preceding to Determination Date d;

Dir$_{d-DirectionLag}$ means the Exposure Direction on Index Business Day d – DirectionLag;

PremE<sub>d</sub> means the Preliminary Exposure of the Underlying Index on Determination Date d;

RiskFactorScalar means the Risk Factor Scalar;

TE_{MAX} means Maximum Target Exposure of the Underlying Index;

TE$_{MIN}$ means Minimum Target Exposure of the Underlying Index;

TH means Exposure Threshold of the Underlying Index;

VT means Volatility Target;

$V_d^U$ means the Volatility of the Underlying Index on Determination Date $d$, calculated as below in Volatility Calculation Section;

## Exposure Direction Calculation

The Exposure Direction Type is defaulted as Long-only:

If Exposure Direction Type is Directional:

$$
Dir_t = 1 \qquad (18)
$$

$$
Dir_t = \begin{cases} SIGN, & if Signal^k_t = 1 \ for \ all \ k \in SignalSet \\ -SIGN, & else \end{cases} \qquad (19)
$$

Where:

Dir$_{t}$ means the Exposure Direction on Index Business Day t;

SIGN means the Sign of Direction;

$Signal^k_t$ means the kth signal in the Signal Set on Index Business Day $t$;

SignalSet means the reference number of the signals in the Signal Set.

Bloomberg Versa Indices Methodology

7

## Bloomberg Versa Indices Methodology

## March 21, 2025

## Underlying Index Volatility Calculation

Index Volatility

The volatility of the Index is either the maximum or the minimum value of the short-term and long-term volatility of the Underlying Index.

If the Volatility Value Selection is Highest:

If the Volatility Value Selection is Average:

$$
V_t^U = max(V_t^1, V_t^2) \times VolAdjustment_{(t-VolAdjLag)} \quad (20)
$$

$$
V_t^U = \frac{V_t^1 + V_t^2}{2} \times VolAdjustment_{(t-VolAdjLag)} \quad (21)
$$

Where:

$t - VolAdjLag$ means the number of Volatility Adjustment Factor Lag Index Business Days immediately preceding to Index Business Day $t$;

$max(a, b)$ means the maximum value of $a$ and $b$;

$min(a, b)$ means the minimum value of $a$ and $b$;

$V_t^1$ means a volatility of the Underlying Index on Index Business Day $t$;

$V_t^2$ means the other volatility of the Underlying Index on Index Business Day $t$;

$V_t^U$ means the volatility of the Underlying Index on Index Business Day $t$;

$VolAdjustment_{t-VolAdjLag}$ means the Volatility Adjustment Factor on the Index Business Day of $t - VolAdjLag$;

$VolAdjLag$ means Volatility Adjustment Factor Lag;

There are multiple Volatility Calculation Types as below:

Exponentially Weighted Moving Average ("EWMA") Volatility

On the Index Business Day immediately preceding the Index Base Date, the variances of the Underlying Index shall be set as below:

$$
Var_t^{ST} = Var_t^{LT} = Var^{Start} = \frac{(V^{Start})^2}{252} \qquad (22)
$$

Thereafter, the variances of the Underlying Index with respect to each Index Business Day $t$, shall be calculated in accordance with the following formula:

Bloomberg Versa Indices Methodology

$$
Var_t^{ST} = \lambda_{ST} \times Var_{t-1}^{ST} + (1 - \lambda_{ST}) \times \left[ \ln \left( \frac{I_t^U}{I_{t-1}^U} \right) \right]^2 \quad (23)
$$

$$
Var_t^{LT} = \lambda_{LT} \times Var_{t-1}^{LT} + (1 - \lambda_{LT}) \times \left[ \ln \left( \frac{I_t^U}{I_{t-1}^U} \right) \right]^2 \quad (24)
$$

8

## Bloomberg Versa Indices Methodology

## March 21, 2025

The EWMA Volatility of the Underlying Index with respect to each Index Business Day $t$, shall be calculated in accordance with the following formula:

$$
V_t^1 = V_t^{ST} = \sqrt{252 \times Var_t^{ST}} \qquad (25)
$$

$$
V_t^2 = V_t^{LT} = \sqrt{252 \times Var_t^{LT}} \qquad (26)
$$

## Where:

$t$ means Index Business Day $t$;

$t-1$ means the Index Business Day immediately preceding Index Business Day $t$;

$\lambda_{ST}$ means Short-Term Lambda;

$\lambda_{LT}$ means Long-Term Lambda;

$I_t^U$ means the level of the Underlying Index on Underlying Index Business Day $t$;

$I_{t-1}^U$ means the level of the Underlying Index on Underlying Index Business Day $t-1$;

$LT$ means the number of Underlying Index Business Days for long-term volatility calculation;

$ST$ means the number of Underlying Index Business Days for short-term volatility calculation;

$Var^{Start}$ means the initial value of the variance of the Underlying Index;

$Var_t^{ST}$ means the short-term index variance of the Underlying Index on Index Business Day $t$;

$Var_t^{LT}$ means the long-term index variance of the Underlying Index on Index Business Day $t$;

$Var_{t-1}^{ST}$ means the short-term index variance of the Underlying Index on Index Business Day $t-1$;

$Var_{t-1}^{LT}$ means the long-term index variance of the Underlying Index on Index Business Day $t-1$;

$V^{Start}$ means the Initial Underlying Index Volatility;

$V_t^{ST}$ means the short-term index volatility of the Underlying Index on Index Business Day $t$;

$V_t^{LT}$ means the long-term index volatility of the Underlying Index on Index Business Day $t$.

## Intraday High Low Volatility

With respect to each Underlying Index, $i$, the volatility for each Index Business Day, $t$, shall be calculated in accordance with the following formulae:

$$
V_t^1 = HLV_t
$$

$$
V_t^2 = LHV_t
$$

(27)

(28)

$$
HLV_t = \sqrt{\ln\left(\frac{HighSnap_t}{LowClose_{t-1}}\right)^2 \times 252} \qquad (29)
$$

Bloomberg Versa Indices Methodology

9

## Bloomberg Versa Indices Methodology

## March 21, 2025

$$
LHV_t = \sqrt{\ln \left( \frac{LowSnap_t}{HighClose_{t-1}} \right)^2 \times 252} \qquad (30)
$$

Where:

$t - 1$ means the Index Business Day immediately preceding Index Business Day $t$;

$HighClose_{t-1}$ means the High Close price on Index Business Day $t - 1$;

$HighSnap_t$ means the High Snap on Index Business Day $t$;

$\ln(x)$ means the natural logarithm of a value $x$;

$LowClose_{t-1}$ means the Low Close price on Index Business Day $t - 1$;

$LowSnap_t$ means the Low Snap on Index Business Day $t$;

$HLV_t$ means the volatility of high/low on Index Business Day $t$;

$LHV_t$ means the volatility of low/high on Index Business Day $t$.

## Signal Calculation

If the Signal Type is Negative Momentum, the value of the signal on Index Business Day *t* is calculated in accordance with the following formulae:

$$
MomSignal_t = \begin{cases} 1, & \text{if } I_t^U < I_{t-m}^U \\ 0, & \text{else} \end{cases} \tag{31}
$$

Where:

$t - m$ means the $m$-th Index Business Day immediately preceding Index Business Day $t$;

$m$ means the Momentum Time Difference;

$I_t^U$ means the level of the Underlying Index on Underlying Index Business Day $t$;

$I_{t-m}^U$ means the level of the Underlying Index on Underlying Index Business Day $t - m$;

If the Signal Type is Increasing Volatility, the value of the signal on Index Business Day $t$ is calculated in accordance with the following formulae:

$$
VolSignal_t = \begin{cases} 1, & \text{if } RV_t > RVAvg_t + \sigma_{RV_t} \\ 0, & \text{else} \end{cases} \tag{32}
$$

Where:

$RV_t$ means the realized volatility of the Underlying Index on Index Business Day $t$ and is calculated in accordance with the following formulae:

$$
RV_t = \sqrt{\frac{1}{l} \times \sum_{k=1}^{l} \left( \ln\left( \frac{I_{t-k+1}^{U}}{I_{t-k}^{U}} \right) \right)^2 \times 252} \quad (33)
$$

Where:

$t - k, t - k + 1, t - i$, means the k-th, (k-1)-th, i-th Index Business Day immediately preceding $t$ respectively;

$I_t^U$ means the level of the Underlying Index on Underlying Index Business Day $t$;

Bloomberg Versa Indices Methodology

10

## Bloomberg Versa Indices Methodology

## March 21, 2025

$I_{t-m}^U$ means the level of the Underlying Index on Underlying Index Business Day $t-m$;

$I_{t-k}^U$ means the level of the Underlying Index on Underlying Index Business Day $t-k$;

$I_{t-k+1}^U$ means the level of the Underlying Index on Underlying Index Business Day $t-k+1$;

$l$ means the RV Lookback Window;

$\ln(x)$ means the natural logarithm of a value $x$;

$RVAvg_t$ means the average realized volatility of the Underlying Index on Index Business Day $t$ and is calculated in accordance with the following formulae:

$$
RVAvg_t = \frac{1}{w} \times \sum_{k=0}^{w-1} RV_{t-k} \qquad (34)
$$

Where:

w means the RV Average Window;

$RV_{t-k}$ means the realized volatility of the Underlying Index on Index Business Day $t-k$;

$\sigma_{RV_t}$ means the volatility of the $RV_t$ on Index Business Day $t$ and is calculated in accordance with the following formulae:

$$
\sigma_{RV_t} = \sqrt{\frac{1}{v-1} \times \sum_{k=0}^{v-1} (RV_{t-k} - \frac{\sum_{i=0}^{v-1} RV_{t-i}}{v})^2} \quad (35)
$$

Where:

$RV_{t-k}$ and $RV_{t-i}$ means the realized volatility of the Underlying Index on Index Business Day $t-k$ and Index Business Day $t-i$ respectively;

v means the RV Sigma Window.

## Glossary for Section 1

<table>
  <tr>
    <td>Actual Exposure</td>
    <td>The exposure of the Underlying Index calculated on Determination Date.</td>
  </tr>
  <tr>
    <td>Cash Index</td>
    <td>The relevant index calculated according to Bloomberg Cash Indices Methodology.</td>
  </tr>
  <tr>
    <td>Day Count Convention</td>
    <td>The number of days.</td>
  </tr>
  <tr>
    <td>Deduction Factor</td>
    <td>The percentage rate deducted daily from the Index Value. Unless specified, the Deduction Factor is zero.</td>
  </tr>
  <tr>
    <td>Determination Date</td>
    <td>For an Index Business Day, the Index Business Day occurring the Determination Lag number of Index Business Days prior.</td>
  </tr>
  <tr>
    <td>Determination Lag</td>
    <td>With respect to an Index Business Day, the number of Index Business Days before such Index Business Day. Unless explicitly stated otherwise in the index specific document, the Determination Lag is one.</td>
  </tr>
  <tr>
    <td>Direction Lag</td>
    <td>With respect to an Index Business Day, the number of Index Business Days before such Index Business Day. Unless explicitly stated otherwise in the index specific document, the Direction Lag is zero.</td>
  </tr>
  <tr>
    <td>Exposure Direction</td>
    <td>The direction of the exposure.</td>
  </tr>
</table>

Bloomberg Versa Indices Methodology

11

## Bloomberg Versa Indices Methodology

## March 21, 2025

<table>
  <tr>
    <td>Exposure Direction Type</td>
    <td>The type of the Exposure Direction, which can be either “Long-only” or “Directional”. Unless explicitly stated otherwise in the index specific document, the Exposure Direction Type is “Long-only”.</td>
  </tr>
  <tr>
    <td>Exposure Threshold</td>
    <td>The percentage exposure that the absolute change in exposure has to be greater than or equal to, for Target Exposure to be equal to Actual Exposure.</td>
  </tr>
  <tr>
    <td>High Close</td>
    <td>The high close values of the Underlying Index.</td>
  </tr>
  <tr>
    <td>High Snap</td>
    <td>The high snap values of the Underlying Index.</td>
  </tr>
  <tr>
    <td>Index Base Date</td>
    <td>The first date on which an Index has a value.</td>
  </tr>
  <tr>
    <td>Index Base Value</td>
    <td>The initial value of an Index.</td>
  </tr>
  <tr>
    <td>Index Business Day</td>
    <td>The days on which the Index is calculated.</td>
  </tr>
  <tr>
    <td>Index Commencement Date</td>
    <td>The date an Index is first made available on the relevant Bloomberg Page.</td>
  </tr>
  <tr>
    <td>Index Currency</td>
    <td>The currency an Index is represented in.</td>
  </tr>
  <tr>
    <td>Index Value</td>
    <td>The value of the Index calculated in accordance with the methodology.</td>
  </tr>
  <tr>
    <td>Initial Underlying Index Volatility</td>
    <td>The initial value of the volatility of the Underlying Index.</td>
  </tr>
  <tr>
    <td>Input Price Lag</td>
    <td>With respect to an Index Business Day, the number of Index Business Days before such Index Business Day. Unless explicitly stated otherwise in the index specific document, the Input Price Lag is zero.</td>
  </tr>
  <tr>
    <td>Low Close</td>
    <td>The low close values of the Underlying Index.</td>
  </tr>
  <tr>
    <td>Low Snap</td>
    <td>The low snap values of the Underlying Index.</td>
  </tr>
  <tr>
    <td>Maximum Target Exposure</td>
    <td>The maximum percentage target exposure of an Underlying Index.</td>
  </tr>
  <tr>
    <td>Minimum Target Exposure</td>
    <td>The minimum percentage target exposure of an Underlying Index.</td>
  </tr>
  <tr>
    <td>Momentum Time Difference</td>
    <td>The integer value day difference that a momentum signal is calculated upon.</td>
  </tr>
  <tr>
    <td>Preliminary Exposure</td>
    <td>The intermediate value that is used for the calculation of Target Exposure.</td>
  </tr>
  <tr>
    <td>Rebalance Date</td>
    <td>Every Index Business Day.</td>
  </tr>
  <tr>
    <td>Rebalance Frequency</td>
    <td>The rate of recurrence to rebalance an Index.</td>
  </tr>
  <tr>
    <td>Risk Factor Scalar</td>
    <td>A scalar to adjust the Preliminary Exposure. Unless explicitly stated otherwise in the index specific document, the Risk Factor Scalar is one.</td>
  </tr>
  <tr>
    <td>RV Average Window</td>
    <td>The integer value of which defines the lookback window of Index Business Days for the RV Average calculation.</td>
  </tr>
  <tr>
    <td>RV Lookback Window</td>
    <td>The integer value of which defines the lookback window of Index Business Days for the RV calculation.</td>
  </tr>
  <tr>
    <td>RV Sigma Window</td>
    <td>The integer value of which defines the lookback window of Index Business Days for the RV Sigma calculation.</td>
  </tr>
  <tr>
    <td>Sign of Direction</td>
    <td>The sign of direction determined according to the signals, which can be either one or minus one. Unless explicitly stated otherwise in the index specific document, the Sign of Direction is equal to one.</td>
  </tr>
  <tr>
    <td>Signal Set</td>
    <td>All the signals used to determine the Sign of Direction.</td>
  </tr>
  <tr>
    <td>Signal Type</td>
    <td>The type of signal calculation to be used in the Exposure Direction calculation, including “Negative Momentum” and “Increasing Volatility”.</td>
  </tr>
  <tr>
    <td>Short-Term Lambda</td>
    <td>The lower weight assigned for the recent variance.</td>
  </tr>
  <tr>
    <td>Long-Term Lambda</td>
    <td>The higher weight assigned for the recent variance.</td>
  </tr>
</table>

Bloomberg Versa Indices Methodology

12

## Bloomberg Versa Indices Methodology

## March 21, 2025

<table>
  <tr>
    <td>Target Exposure</td>
    <td>The target exposure of the Underlying Index calculated on Determination Date.</td>
  </tr>
  <tr>
    <td>Target Exposure Type</td>
    <td>The type of calculation method of Target Exposure, which can be either “Standard Target Exposure” or “Target Exposure with Risk Factor Scalar”. Unless explicitly stated otherwise in the index specific document, the Target Exposure Type is “Standard Target Exposure”.</td>
  </tr>
  <tr>
    <td>Transaction Cost Rate</td>
    <td>The rate at which costs are incurred during the rebalancing process. Unless explicitly stated otherwise in the index specific document, the Transaction Cost Rate is zero.</td>
  </tr>
  <tr>
    <td>Underlying Index</td>
    <td>The index that the Volatility Target Index is based on.</td>
  </tr>
  <tr>
    <td>Underlying Index Business Day</td>
    <td>A business day that the Underlying Index is calculated.</td>
  </tr>
  <tr>
    <td>Volatility Adjustment Factor</td>
    <td>The adjustment to the volatility of the Underlying Index.</td>
  </tr>
  <tr>
    <td>Volatility Adjustment Factor Lag</td>
    <td>With respect to an Index Business Day, the number of Index Business Days before such Index Business Day. Unless explicitly stated otherwise in the index specific document, the Volatility Adjustment Factor Lag is one.</td>
  </tr>
  <tr>
    <td>Volatility Calculation Type</td>
    <td>The volatility calculation method for the Underlying Index.</td>
  </tr>
  <tr>
    <td>Volatility Value Selection</td>
    <td>The selection among the different volatility values of the Underlying Index, which can be either “Highest”, “Lowest” or “Average”. Unless explicitly stated otherwise in the index specific document, the default is “Highest”.</td>
  </tr>
  <tr>
    <td>Volatility Target</td>
    <td>The percentage target of volatility of an Index.</td>
  </tr>
</table>

Bloomberg Versa Indices Methodology

13

## Bloomberg Versa Indices Methodology

## March 21, 2025

## Section 2: Calculation of the Dynamic Treasury Volatility Target Index

## Index Value Calculation

The Index Value on the Index Base Date shall be the Index Base Value. Thereafter, the Index Value with respect to each subsequent Index Business Day, t, shall be calculated in accordance with the following formula:

$$
I_t = I_{t-1} + UnitsReturn_t - FC_t - TC_{t-1} \quad (1)
$$

Where:

$t-1$ means the Index Business Day immediately preceding $t$;

$FC_t$ means the Funding Cost on Index Business Day $t$;

$I_t$ and $I_{t-1}$ means the Index Values on Index Business Day $t$ and on Index Business Day $t-1$ respectively;

UnitsReturn$_{t}$ means the return attributed to the Units on Index Business Day $t-1$, calculated in accordance with the following formula:

Where:

i means a Constituent;

$$
UnitsReturn_t = \sum_{i \in IndexConstituents} U_{t-1}^i \times (P_t^i - P_{t-1}^i) \quad (2)
$$

$U_{t-1}^i$ means the Units for Constituent $i$ on Index Business Day $t-1$;

$P_t^i$ means the Price of Constituent i on Index Business Day t;

$P_{t-1}^i$ means the Price of Constituent $i$ on Index Business Day $t-1$;

$TC_{t-1}$ means the Transaction Cost on Index Business Day $t-1$.

## Units

With respect to each Constituent, i, the Units for each Index Business Day, t, shall be calculated in accordance with the following formulae:

If Index Business Day $t$ is the Index Base Date:

Thereafter:

$$
U_t^i = W_t^i \times \frac{I_B}{P_t^i} \qquad (3)
$$

$$
U_t^i = W_t^i \times \frac{I_{t-1}}{P_{t-1}^i} \qquad (4)
$$

Where:

$t-1$ means the Index Business Day immediately preceding $t$;

$I_B$ means the Index Base Value;

$I_{t-1}$ means the Index Value on Index Business Day $t-1$;

$P_t^i$ means the Price of Constituent $i$ on Index Business Day $t$;

$P_{t-1}^i$ means the Price of Constituent $i$ on Index Business Day $t-1$;

Bloomberg Versa Indices Methodology

14

## Bloomberg Versa Indices Methodology

$U_t^i$ means the Units for Constituent $i$ on Index Business Days $t$;

$W_t^i$ means the Weight for Constituent $i$ on Index Business Day $t$.

## March 21, 2025

## Weights

With respect to each Constituent, $i$, the Weight for each Index Business Day, $t$, shall be calculated in accordance with the following formulae:

If Exposure Weight Ceiling or Exposure Weight Floor specified for any Constituent, i:

Otherwise:

$$
W_t^i = \begin{cases} Dir_{t-1} \times \min \left( R^i, \frac{VT^i}{Vol_t^i} \right) & \text{if } Dir_{t-1} < EWC \text{ or } Dir_{t-1} > EWF \\ 0 & \text{else} \end{cases} \qquad (5)
$$

$$
W_t^i = Dir_{t-1} \times \min(R^i, \frac{VT^i}{Vol_t^i}) \qquad (6)
$$

Where:

$Dir_{t-1}$ means the Exposure Direction on Index Business Day $t-1$;

$EWC$ means the Exposure Weight Ceiling for the Constituent $i$;

$EWF$ means the Exposure Weight Floor for the Constituent $i$;

$R^i$ means the Rapid Risk Volatility Ceiling for Constituent $i$;

$VT^i$ means the Volatility Target for Constituent $i$;

$Vol_t^i$ means the Constituent Volatility for Constituent $i$ on Index Business Day $t$;

$W_t^i$ means the Weight for Constituent $i$ on Index Business Day $t$.

## Volatility

With respect to each Constituent, $i$, the Constituent Volatility for each Index Business Day, $t$, shall be calculated in accordance with the following formulae:

Where:

$$
Vol_t^i = \frac{Vol\_HL_t^i + Vol\_LH_t^i}{2} \qquad (7)
$$

$$
Vol\_HL_t^i = \sqrt{\ln\left(\frac{HighSnap_t^i}{LowClose_{t-1}^i}\right)^2 \times 252} \qquad (8)
$$

$$
Vol\_LH_t^i = \sqrt{\ln\left(\frac{LowSnap_t^i}{HighClose_{t-1}^i}\right)^2 \times 252} \qquad (9)
$$

Where:

$t - 1$ means the Index Business Day immediately preceding $t$;

$HighClose_{t-1}^i$ means the High Close price for the Constituent $i$, on Index Business Day $t - 1$;

$HighSnap_t^i$ means the High Snap for the Constituent $i$, on Index Business Day $t$;

Bloomberg Versa Indices Methodology

15

Bloomberg Versa Indices Methodology

$\ln(x)$ means the natural logarithm of a value x;

$LowClose_{t-1}^i$ means the Low Close price for the Constituent $i$, on Index Business Day $t-1$;

$LowSnap_t^i$ means the Low Snap for the Constituent $i$, on Index Business Day $t$;

$Vol_t^i$ means the Constituent Volatility for the Constituent $i$, on Index Business Day $t$;

$Vol_{HL}^t_i$ means the volatility of high/low for the Constituent $i$, on Index Business Day $t$;

$Vol_{LH}^t_i$ means the volatility of low/high for the Constituent $i$, on Index Business Day $t$.

## March 21, 2025

## Exposure Direction

If Exposure Direction Type is Long-only:

$$
Dir_t = 1 \qquad (10)
$$

If Exposure Direction Type is Directional:

$$
Dir_t = \begin{cases} -1 & \text{if Signal1}_t = -1 \text{ and Signal2}_t = -1 \\ 1 & \text{else} \end{cases} \qquad (11)
$$

Where:

$t$ means the current Index Business Day;

$Dir_t$ means the Exposure Direction on Index Business Day $t$;

$Signal1_t$ means the value of the SignalType1 on Index Business Day $t$ calculated by the respective formula for SignalType1 in the Signal Type section;

$Signal2_t$ means the value of the SignalType2 on Index Business Day $t$ calculated by the respective formula for SignalType2 in the Signal Type section.

## Signal Type

If the SignalType is Yield Momentum, the value of the signal on Index Business Day $t$ is calculated in accordance with the following formulae:

$$
YieldMom_t = \begin{cases} -1 & if \Delta YMA_t > \sigma_{\Delta YMA_t} \\ 1 & else \end{cases} \qquad (12)
$$

$$
YMA_t = \frac{1}{l} \times \sum_{k=0}^{l-1} LongYield_{t-k} \qquad (13)
$$

$$
\Delta YMA_t = YMA_t - YMA_{t-m} \qquad (14)
$$

$$
\sigma_{\Delta YMA_t} = \sqrt{\frac{1}{v-1} \times \sum_{i=0}^{v-1} \left( \Delta YMA_{t-i} - \frac{\sum_{k=0}^{v-1} \Delta YMA_{t-k}}{v} \right)^2} \quad (15)
$$

Where:

$t-k, t-m$ and $t-i$ means the k-th, m-th and i-th Index Business Day immediately preceding $t$ respectively;

$\Delta YMA_t$ means the change of the moving average of the values of the Yield Component on Index Business Day $t$;

$LongYield_{t-k}$ means the value of the Yield Component with constituent tag of "Long" on Index Business Day $t-k$;

$m$ means the Momentum Time Difference;

Bloomberg Versa Indices Methodology

16

## Bloomberg Versa Indices Methodology

## March 21, 2025

l means the Yield Lookback Window;

$\sigma_{\Delta YMA_t}$ means the standard deviation of $\Delta YMA_t$;

v means the Yield Sigma Window;

$YMA_t$ and $YMA_{t-m}$ means the moving average of the values of the Yield Component on Index Business Day $t$ and Index Business Day $t-m$ respectively.

If the Signal Type is Curve Momentum, the value of the signal on Index Business Day $t$ is calculated in accordance with the following formulae:

$$
CurveMom_t = \begin{cases} -1 & \text{if } \Delta CMA_t < -\sigma_{\Delta CMA_t} \\ 1 & \text{else} \end{cases} \qquad (16)
$$

$$
CMA_t = \frac{1}{j} \times \sum_{k=0}^{j-1} (LongYield_{t-k} - ShortYield_{t-k}) \qquad (17)
$$

$$
\Delta CMA_t = CMA_t - CMA_{t-m} \qquad (18)
$$

$$
\sigma_{\Delta CMA_t} = \sqrt{\frac{1}{n-1} \times \sum_{i=0}^{n-1} \left( \Delta CMA_{t-i} - \frac{\sum_{k=0}^{n-1} \Delta CMA_{t-k}}{n} \right)^2} \qquad (19)
$$

Where:

$t-k, t-m$ and $t-i$ means the k-th, m-th and i-th Index Business Day immediately preceding $t$ respectively;

$CMA_t$ means the moving average of curve values on Index Business Day $t$;

$\Delta CMA_t$ means the change of the moving average of curve values on Index Business Day $t$;

$i$ means a Constituent;

$j$ means the Curve Lookback Window;

$LongYield_{t-k}$ means the value of the Yield Component with constituent tag of "Long" on Index Business Day $t-k$;

$m$ means the Momentum Time Difference;

$n$ means the Curve Sigma Window;

$ShortYield_{t-k}$ means the value of the Yield Component with constituent tag of "Short" on Index Business Day $t-k$;

$\sigma_{\Delta CMA_t}$ means the standard deviation of the change of the moving average of curve values on Index Business Day $t$.

## Funding Cost

If a Funding Cost Rate is specified, then the Funding Cost is calculated in accordance with the following formulae:

If the Index Business Day, *t*, is the Index Base Date:

$$
FC_t = 0 \tag{20}
$$

Thereafter:

Where:

$$
FC_t = \frac{FCR_{t-1}}{100} \times DCFC_{t-1,t} \times \sum_{i \in IndexConstituents} (U_{t-1}^i \times P_{t-1}^i) \quad (21)
$$

Bloomberg Versa Indices Methodology

17

## Bloomberg Versa Indices Methodology

## March 21, 2025

t - 1 means the Index Business Day immediately preceding t;

$DCFC_{t-1,t}$ means the amount of calendar days from and including Index Business Day $t-1$ to and excluding Index Business Day $t$, divided by 365;

$FCR_{t-1}$ means the Funding Cost Rate on Index Business Day immediately preceding $t$. If the Index Business Day immediately preceding $t$ falls on a SIFMA holiday, then use the most recently available rate;

i means a Constituent;

IndexConstituents means the given Index Constituents;

$P_{t-1}^i$ means the Price of Constituent $i$ on Index Business Day $t-1$;

$U_{t-1}^l$ means the Units for Constituent $i$ on Index Business Day $t-1$.

If no Funding Cost Rate is specified, then the Funding cost is calculated in accordance with the following formulae:

$$
FC_t = 0 \tag{22}
$$

## Transaction Cost

The Transaction Cost for each Index Business Day, t, is calculated in accordance with the following formulae:

If the Index Business Day, t, is the Index Base Date:

Thereafter:

$$
TC_t = 0 \qquad (23)
$$

Where:

$$
TC_t = TCR^i \times \sum_{i \in IndexConstituents} abs(U_t^i - U_{t-1}^i) \times P_t^i \quad (24)
$$

t - 1 means the Index Business Day immediately preceding t;

abs(x) means the absolute value of x;

i means a Constituent;

IndexConstituents mean the given Index Constituents;

$P_t^i$ means the Price of Constituent i on Index Business Day t;

TCR$^i$ means the Transaction Cost for Constituent $i$;

$U_t^i$ and $U_{t-1}^i$ mean the Units for Constituent $i$ on Index Business Day $t$ and Index Business Day $t-1$ respectively.

## Glossary for Section 2

<table>
  <tr>
    <td>Constituent</td>
    <td>An Underlying Index.</td>
  </tr>
  <tr>
    <td>Constituent Volatility</td>
    <td>The volatility of the given Constituent.</td>
  </tr>
  <tr>
    <td>Curve Lookback Window</td>
    <td>The integer value of which defines the lookback window of Index Business Days for the Spread calculation.</td>
  </tr>
  <tr>
    <td>Curve Sigma Window</td>
    <td>The integer value of which defines the lookback window of Index Business Days for the Spread Sigma calculation.</td>
  </tr>
  <tr>
    <td>Exposure Direction</td>
    <td>The exposure signal that is calculated dependent on the Exposure Direction Type.</td>
  </tr>
  <tr>
    <td>Exposure Direction Type</td>
    <td>The types of Exposure Direction calculation to be used in the index, including Long-only and Long-short.</td>
  </tr>
  <tr>
    <td>Exposure Weight Ceiling</td>
    <td>The highest value of the exposure.</td>
  </tr>
</table>

Bloomberg Versa Indices Methodology

18

## Bloomberg Versa Indices Methodology

## March 21, 2025

<table>
<tr>
<td>Exposure Weight Floor</td>
<td>The lowest value of the exposure.</td>
</tr>
<tr>
<td>Funding Cost</td>
<td>The cost of financing.</td>
</tr>
<tr>
<td>Funding Cost Rate</td>
<td>The given rate of cost of financing.</td>
</tr>
<tr>
<td>High Close</td>
<td>The high close values of a Constituent.</td>
</tr>
<tr>
<td>High Snap</td>
<td>The high snap values of a Constituent.</td>
</tr>
<tr>
<td>Index</td>
<td>Has the meaning set forth in the Introduction.</td>
</tr>
<tr>
<td>Index Base Date</td>
<td>The first date on which an Index publishes a value.</td>
</tr>
<tr>
<td>Index Base Value</td>
<td>The value of an Index on and prior to the Index Base Date.</td>
</tr>
<tr>
<td>Index Business Day</td>
<td>The days on which the Index is calculated.</td>
</tr>
<tr>
<td>Index Constituents</td>
<td>All the Constituents for an Index.</td>
</tr>
<tr>
<td>Index Currency</td>
<td>The currency in which an index is published.</td>
</tr>
<tr>
<td>Index Value</td>
<td>The value of the Index calculated in accordance with the methodology.</td>
</tr>
<tr>
<td>Low Close</td>
<td>The low close values of a Constituent.</td>
</tr>
<tr>
<td>Low Snap</td>
<td>The low snap values of a Constituent.</td>
</tr>
<tr>
<td>Market Close Time</td>
<td>The given time of market closure for a given Constituent.</td>
</tr>
<tr>
<td>Market Close Time Partial</td>
<td>The given time of market closure for a given Constituent on a partial holiday.</td>
</tr>
<tr>
<td>Observation Business Days</td>
<td>The days from which data used for making determinations may be taken.</td>
</tr>
<tr>
<td>Price</td>
<td>The value of such Constituent as determined from the Price Source.</td>
</tr>
<tr>
<td>Rapid Risk Volatility Ceiling</td>
<td>The maximum weight that can be achieved by a Constituent.</td>
</tr>
<tr>
<td>Signal Type</td>
<td>The type of signal calculation to be used in the Exposure Direction calculation, including Yield Momentum, and Curve Momentum.</td>
</tr>
<tr>
<td>Snap End Time</td>
<td>The end time used for the snap data acquisition.</td>
</tr>
<tr>
<td>Snap End Time Partial</td>
<td>The end time used for the snap data acquisition on a partial holiday.</td>
</tr>
<tr>
<td>Snap Start Time</td>
<td>The start time used for the snap data acquisition.</td>
</tr>
<tr>
<td>Snap Switch Date</td>
<td>The date at which intraday snaps are used as the pricing source for HighSnap and LowSnap.</td>
</tr>
<tr>
<td>Trading Day</td>
<td>The days on which an index considers that a Constituent can be traded.</td>
</tr>
<tr>
<td>Transaction Cost</td>
<td>The estimated expenses of executing transactions.</td>
</tr>
<tr>
<td>Transaction Cost Rate</td>
<td>The rate at which costs are incurred during the rebalancing process.</td>
</tr>
<tr>
<td>Underlying Index</td>
<td>An index that is a Constituent of the Index.</td>
</tr>
<tr>
<td>Units</td>
<td>The number of units of each Constituent held on an Index Business Day.</td>
</tr>
<tr>
<td>Volatility Target</td>
<td>The intended target volatility for the index.</td>
</tr>
<tr>
<td>Weight</td>
<td>The intended weight of a Constituent that an Index uses to determine the Target Units.</td>
</tr>
<tr>
<td>Yield Component</td>
<td>The component used to obtain the yield of the Index Constituent.</td>
</tr>
<tr>
<td>Yield Lookback Window</td>
<td>The integer value of which defines the lookback window of Index Business Days for the Yield calculation.</td>
</tr>
<tr>
<td>Yield Sigma Window</td>
<td>The integer value of which defines the lookback window of Index Business Days for the Yield Sigma calculation.</td>
</tr>
</table>

Bloomberg Versa Indices Methodology

19

## Bloomberg Versa Indices Methodology

## March 21, 2025

## Section 3: Calculation of the Multi-Asset Basket Index

## Index Value Calculation

With respect to each Index, the Closing Index Value on the Index Base Date shall be the Index Base Value. Thereafter, the Closing Index Value with respect to each subsequent Index Business Day, t, and Fixing, f, shall be calculated in accordance with the following formula:

$$
I_{\langle t, f \rangle} = I_{\langle t-1, close \rangle} + UnitsReturn_{\langle t, f \rangle} + IndexAdjustment_{\langle t, f \rangle} \quad (1)
$$

Where:

t - 1 means the Index Business Day immediately preceding t;

close means the Closing Fixing;

$I_{\langle t, f \rangle}$ and $I_{\langle t-1, close \rangle}$ mean the Index Values for Fixing $f$ on Index Business Day $t$ and the Closing Fixing on Index Business Day $t-1$ respectively;

UnitsReturn$_{<t,f>}$ means the return attributed to the Units at Fixing f on Index Business Day t, calculated in accordance with the following formula:

$$
UnitsReturn_{\langle t, f \rangle} = UnitsReturn_{\langle t, f \rangle}^{Funded} + UnitsReturn_{\langle t, f \rangle}^{Unfunded} \quad (2)
$$

$$
UnitsReturn_{\langle t,f \rangle}^{Funded} = \sum_{i \in FundedConstituents} U_t^i \times (P_{\langle t,f \rangle}^i \times FX_{\langle t,f \rangle}^i - P_{\langle t-1,close \rangle}^i \times FX_{\langle t-1,close \rangle}^i) \quad (3)
$$

$$
UnitsReturn_{\langle t, f \rangle}^{Unfunded} = \sum_{i \in UnfundedConstituents} U_t^i \times (P_{\langle t, f \rangle}^i - P_{\langle t-1, close \rangle}^i) \times FX_{\langle t, f \rangle}^i \quad (4)
$$

Where:

$UnitsReturn_{(t,f)}^{Funded}$ and $UnitsReturn_{(t,f)}^{Unfunded}$ mean the return attributed to the Units at Fixing $f$ on Index Business Day $t$ for the Funded Constituents and Unfunded Constituents respectively;

FundedConstituents and UnfundedConstituents mean the sets of Funded Constituents and Unfunded Constituents respectively;

i means a Constituent;

$U_t^i$ means the Units for Constituent $i$ on Index Business Day $t$;

$P_{\langle t, f \rangle}^i$ means the Price of Constituent $i$ at Fixing $f$ on Index Business Day $t$;

$P_{\langle t-1, close \rangle}^i$ means the Price of Constituent $i$ at the Closing Fixing on Index Business Day $t-1$;

$FX_{t,f}^i$ means the Spot Exchange Rate to convert one unit of the Constituent Currency of Constituent $i$ to the Index Currency at Fixing $f$ on Index Business Day $t$; and

$FX_{t-1,close}^i$ means the Spot Exchange Rate to convert one unit of the Constituent Currency of Constituent $i$ to the Index Currency at the Closing Fixing on Index Business Day $t-1$.

Bloomberg Versa Indices Methodology

20

## Bloomberg Versa Indices Methodology

## March 21, 2025

IndexAdjustment$_{<t,f>}$ means the Index Adjustment at Fixing $f$ on Index Business Day $t$ calculated in accordance with the following formula:

$$
IndexAdjustment_{(t,f)} = \sum_{a \in Adjustments_{(t,f)}} a \qquad (5)
$$

Where:

Adjustments$_{<t,f>}$ means the set of Adjustment Values on Index Business Day $t$ with Fixings up to and including Fixing $f$; and $a$ means an Adjustment Value.

## Units

With respect to each Constituent, i, the Units on the Index Base Date shall be 0 (zero). Thereafter, the Units with respect to each Constituent, i, and subsequent Index Business Day, t, shall be calculated in accordance with the following formula:

$$
U_t^i = U_{t-1}^i + IU_{t-1}^i \qquad (6)
$$

Where:

$t-1$ means the Index Business Day immediately preceding $t$;

$U_t^i$ and $U_{t-1}^i$ mean the Units for Constituent $i$ on Index Business Days $t$ and $t-1$ respectively; and

IU$_{t-1}$$^{i}$ means the Incremental Units for Constituent $i$ on Index Business Day $t-1$.

## Incremental Units

With respect to each Constituent, $i$, if the Rebalance Length is one, the Incremental Units for each Index Business Day, $t$, shall be calculated on the Units Determination Date for $t$, else, the Incremental Units for each Index Business Day, $t$, shall be calculated in accordance with the following formulae:

If Index Business Day $t$ is the Index Base Date:

$$
IU_t^i = TEU_d^i \qquad (7)
$$

Else if Index Business Day $t$ is a Rebalance Day:

Else:

$$
IU_t^i = (TEU_d^i - U_d^i) \times \frac{1}{RL^i} \qquad (8)
$$

$$
IU_t^i = 0 \qquad (9)
$$

Where:

RL$^i$ means the Rebalance Length for Constituent i;

IU$_{t}$$^{i}$ means the Incremental Units for Constituent i on Index Business Day t ;

$U_d^i$ means the Units for Constituent $i$ on Units Determination Date $d$;

Bloomberg Versa Indices Methodology

21

## Bloomberg Versa Indices Methodology

## March 21, 2025

$TEU_d^i$ means the Target Ending Units for Constituent $i$ on Units Determination Date $d$ (if Units Determination Lag is zero, Units Determination Date is the Rebalance Start Date), and shall be calculated in accordance with the following formula:

$$
TEU_d^i = \frac{I_{\langle obs_t(I), close \rangle} \times W_{obs_t(W)}^i}{P_{\langle obs_t(P^i), close \rangle}^i \times FX_{\langle obs_t(FX^i), close \rangle}^i} \qquad (10)
$$

Where:

*close* means the Closing Fixing;

$obs_t(I)$, $obs_t(P^i)$ and $obs_t(FX^i)$ mean, with respect to Index Business Day $t$, the Observation Dates for Index, $I$, Price of Constituent $i$, $P^i$, and Spot Exchange Rate to convert one unit of the Price Currency of Constituent $i$ to the Index Currency, $FX^i$;

$I_{\langle obs_t(I), close \rangle}$ means the Index Value for the Closing Fixing on Observation Date $obs_t(I)$;

$P^i_{\langle obs_t(P^i), close \rangle}$ means the Price of Constituent $i$ for the Closing Fixing on Observation Date $obs_t(P^i)$;

$FX^i_{\langle obs_t(FX^i), close \rangle}$ means the Spot Exchange Rate to convert one unit of the Price Currency of Constituent $i$ to the Index Currency at Closing Fixing on Observation Date $obs_t(FX^i)$; and

$W^i_{obs_t(W)}$ means the Weight of Constituent $i$ on Observation Date $obs_t(W)$.

## Adjustments

With respect to each Index, the set of Adjustment Values on the Index Base Date shall be defaulted to 0 (zero). Thereafter, the set of Adjustment Values with respect to each Index and subsequent Index Business Day, t, with Fixings up to and including Fixing f, shall be calculated in accordance with the following formula:

$$
\textit{Adjustments}_{\langle t, f \rangle} = \{ \textit{tc}_t^i | i \in \textit{Constituents} \} \qquad (11)
$$

Where:

i means a Constituent;

Constituents is the set of Funded and Unfunded Constituents;

$tc_t^i$ means the Transaction Cost of Constituent i on Index Business Day t, calculated in accordance with the following formula:

$$
tc_t^i = -(\text{abs}(IU_t^i) \times P_{\langle t,f \rangle}^i \times TCR^i) \quad (12)
$$

Where:

IU$_{t}$$^{i}$ means the Incremental Units for Constituent $^{i}$ on Index Business Day $^{t}$;

$P_{\langle t,f \rangle}^i$ means the Price of Constituent $i$ at Fixing $f$ on Index Business Day $t$;

TCR$^i$ means the Transaction Cost Rate for Constituent $i$;

## Weights

With respect to each Constituent i, the Weights shall be determined on the Units Determination Date in accordance with the Weighting Scheme:

Bloomberg Versa Indices Methodology

22

## Bloomberg Versa Indices Methodology

For the Weighting Scheme that is “Fixed Weighting”:

## March 21, 2025

$$
W_d^i = FixedWeight^i \qquad (13)
$$

For the Weighting Scheme that is “Signal-Based Weighting”:

$$
W_d^i = FixedWeight^i \times MASignal_d^i \qquad (14)
$$

Where:

i means a Constituent;

$W_d^i$ means the Weight of Constituent i on Units Determination Date d;

$FixedWeight^i$ means the Fixed Weights of Constituent i;

$MASignal_d^i$ means the Multi-Asset Signal of Constituent i for on Units Determination Date d.

## Multi-Asset Signal

With respect to each Constituent, $i$, whose Weighting Scheme is "Signal-Based Weight", the Multi-Asset Signal for each Index Business Day, $t$, shall be calculated in accordance with the following formulae:

If $1YReturn_t^i \ge min(1YReturn_t^i | i \in F)$ or $t \le Index Base Date + 252$:

Else:

$$
MASignal_t^i = 1 \qquad (15)
$$

$$
MASignal_t^i = 0 \qquad (16)
$$

Where:

$F$ means the set of Constituents whose Weighting Scheme is "Fixed Weighting";

$t-1$ means the Index Business Day immediately preceding $t$;

*Index Base Date* + 252 means the Index Business Day that is 252 Index Business Days immediately following the Index Base Date;

$MASignal_i^t$ means the Multi-Asset Signal of Constituent $i$ on Index Business Day $t$;

$1YReturn_i^t$ means the 1-year return of Constituent $i$ on Index Business Day $t$, as calculated in accordance with the following formula:

$$
1YReturn_t^i = \frac{P_t^i}{P_{t-251}^i} - 1 \qquad (17)
$$

Where:

$t - 251$ means 251 Index Business Days immediately preceding $t$; and

$P_t^i$ and $P_{t-251}^i$ mean the Price of Constituent $i$ on Index Business Day $t$ and $t - 251$ respectively.

Bloomberg Versa Indices Methodology

23

## Bloomberg Versa Indices Methodology

## March 21, 2025

## Glossary for Section 3

<table>
<tr>
<td>Adjustment Value</td>
<td>The Holding Cost or Transaction Cost.</td>
</tr>
<tr>
<td>Closing Fixing</td>
<td>The Fixing corresponding to the end of day valuation.</td>
</tr>
<tr>
<td>Closing Index Value</td>
<td>The value of the Index on any given Index Business Day at the Closing Fixing.</td>
</tr>
<tr>
<td>Constituents</td>
<td>The Funded and Unfunded Constituents.</td>
</tr>
<tr>
<td>Data Field</td>
<td>The type of field used for input calculation.</td>
</tr>
<tr>
<td>Fixed Weight</td>
<td>For each Constituent, its specified weight.</td>
</tr>
<tr>
<td>Fixed Weighting</td>
<td>A type of Weighting Schemes.</td>
</tr>
<tr>
<td>Fixing</td>
<td>A given time specified with respect to a location or time zone.</td>
</tr>
<tr>
<td>Funded Constituent</td>
<td>An Underlying Index for which it is considered that the notional value is exchanged.</td>
</tr>
<tr>
<td>FX Data Source</td>
<td>The source of FX data for a Fixing.</td>
</tr>
<tr>
<td>Holding Cost</td>
<td>The cost of holding the constituents in the Index.</td>
</tr>
<tr>
<td>Holding Cost Factor</td>
<td>The factor applied to Holding Cost.</td>
</tr>
<tr>
<td>Incremental Units</td>
<td>The difference in Units attributed to an action or activity on a Fixing.</td>
</tr>
<tr>
<td>Index</td>
<td>Has the meaning set forth in the Introduction.</td>
</tr>
<tr>
<td>Index Base Date</td>
<td>The first date on which an Index publishes a value. For the avoidance of doubt, the Index Base Date is also a Rebalance Start Date.</td>
</tr>
<tr>
<td>Index Base Value</td>
<td>The value of an Index on and prior to the Index Base Date.</td>
</tr>
<tr>
<td>Index Business Day</td>
<td>The days on which the Index is calculated.</td>
</tr>
<tr>
<td>Index Commencement Date</td>
<td>The date on which an index is first published.</td>
</tr>
<tr>
<td>Index Currency</td>
<td>The currency in which an index is published.</td>
</tr>
<tr>
<td>Index Value</td>
<td>The value of the Index at a given Fixing on an Index Business Day.</td>
</tr>
<tr>
<td>Market Disruption Cut-off Date</td>
<td>The date on which an ongoing Market Disruption Event shall be deemed to have ended for the purpose of applying the Rebalance Disruption Rule. Unless explicitly stated otherwise in the index specific document, such date will be the Rebalance Business Day immediately preceding the next Units Determination Date.</td>
</tr>
<tr>
<td>Multi-Asset Signal</td>
<td>The data that is used to calculate the Weight of the Constituent.</td>
</tr>
<tr>
<td>Observation Business Days</td>
<td>The days from which data used for making determinations may be taken.</td>
</tr>
<tr>
<td>Observation Date</td>
<td>With respect to an Index Business Day and a Data Field, it is the Observation Business Day occurring the Observation Lag number of Observation Business Days prior to its Units Determination Date. If such day is not an Observation Business Day, then the immediately preceding Observation Day.</td>
</tr>
<tr>
<td>Observation Lag</td>
<td>With respect to a Data Field, the number of Observation Business Days for which inputs used for any calculation may be lagged. Unless specified for a given Data Field, the Observation Lag is zero.</td>
</tr>
<tr>
<td>Price</td>
<td>If the Constituent is not a Timezone Lagged Constituent and the date for which the Price is with respect to is a Pricing Day, the value of a Constituent as determined from the Price Source with respect to the Fixing. Otherwise, the value of such Constituent as determined from the Price Source with respect to the Closing Fixing on the immediately preceding Pricing Day.</td>
</tr>
<tr>
<td>Price Currency</td>
<td>The currency in which the Prices of the Constituents are quoted.</td>
</tr>
<tr>
<td>Price Source</td>
<td>The source of pricing to be used for each Constituent and Fixing.</td>
</tr>
<tr>
<td>Pricing Day</td>
<td>The days on which Prices for a Constituent are considered to be available.</td>
</tr>
<tr>
<td>Rebalance Business Days</td>
<td>The days on which a rebalancing action may be performed.</td>
</tr>
<tr>
<td>Rebalance Day</td>
<td>Each day within a Rebalance Period that is a Rebalance Business Day.</td>
</tr>
<tr>
<td>Rebalance Disruption Rule</td>
<td>The set of rules by which a rebalance will be adjusted in the event of certain Market Disruption Events. See Appendix II.</td>
</tr>
<tr>
<td>Rebalance End Date</td>
<td>The Rebalance Business Day occurring the number of Rebalance Length minus one (1) Rebalance Business Days after the Rebalance Start Date. If such date is after the Market Disruption Cut-off Date, then it is the Market Disruption Cut-off Date. For the avoidance of doubt, if the Rebalance Length is one (1), then the Rebalance End Date is the Rebalance Start Date.</td>
</tr>
</table>

Bloomberg Versa Indices Methodology

24

## Bloomberg Versa Indices Methodology

## March 21, 2025

<table>
  <tr>
    <td>Rebalance Length</td>
    <td>With respect to a Constituent, the number of Rebalance Business Days over which a rebalance is performed. For the avoidance of doubt, the Rebalance Length on Index Base Date is always one (1).</td>
  </tr>
  <tr>
    <td>Rebalance Period</td>
    <td>The set of Rebalance Business Days from, and including, each Rebalance Start Date to, and including, the corresponding Rebalance End Date.</td>
  </tr>
  <tr>
    <td>Rebalance Start Date</td>
    <td>The Rebalance Business Day on which a Rebalance Period is scheduled to begin.</td>
  </tr>
  <tr>
    <td>Signal-Based Weighting</td>
    <td>A type of Weighting Schemes.</td>
  </tr>
  <tr>
    <td>Spot Exchange Rate</td>
    <td>The rate used to convert one unit of a Price Currency into the Index Currency at a given Fixing on an Index Business Day as determined from the FX Data Source. Otherwise, the rate as determined from the FX Data Source with respect to the Closing Fixing on the immediately preceding Index Business Day.</td>
  </tr>
  <tr>
    <td>Target Units</td>
    <td>The Units of a Constituent that an index intends to hold after trading activities are performed.</td>
  </tr>
  <tr>
    <td>Trade Disruption Handling</td>
    <td>The way the Index handles a rebalance in the event of certain Market Disruption Events. See Appendix II.</td>
  </tr>
  <tr>
    <td>Transaction Cost</td>
    <td>The cost of trading the Constituents in the Index.</td>
  </tr>
  <tr>
    <td>Transaction Cost Rate</td>
    <td>The rate at which costs are incurred during the rebalancing process.</td>
  </tr>
  <tr>
    <td>Timezone Lagged Constituent</td>
    <td>A Constituent for which a lag is applied to account for the notional location of the Constituent relative to that of the Index.</td>
  </tr>
  <tr>
    <td>Underlying Index</td>
    <td>An index that is a Constituent of the Index.</td>
  </tr>
  <tr>
    <td>Unfunded Constituent</td>
    <td>An Underlying Index for which it is considered that the notional value is not exchanged.</td>
  </tr>
  <tr>
    <td>Units</td>
    <td>The number of units of each Constituent held on opening of an Index Business Day.</td>
  </tr>
  <tr>
    <td>Units Determination Business Days</td>
    <td>The days on which an index may make determinations with respect to changing units.</td>
  </tr>
  <tr>
    <td>Units Determination Date</td>
    <td>For an Index Business Day, the Units Determination Business Day occurring the Units Determination Lag number of Units Determination Business Days prior. If such day is not an Index Business Day, then the immediately preceding Units Determination Business Day. Such day will not change in the event of a Market Disruption Event.</td>
  </tr>
  <tr>
    <td>Units Determination Lag</td>
    <td>The number of Units Determination Business Days before any units determinations made by an index should become effective. Unless specified otherwise, the Units Determination Lag is zero.</td>
  </tr>
  <tr>
    <td>Weight</td>
    <td>The intended weight of a Constituent that an Index uses to determine the Target Units.</td>
  </tr>
  <tr>
    <td>Weighting Scheme</td>
    <td>The method used to allocate Weights to the Constituents.</td>
  </tr>
</table>

Bloomberg Versa Indices Methodology

25

## Bloomberg Versa Indices Methodology

## March 21, 2025

## Section 4: Backtest assumptions

The rules outlined above are applied historically, however the following assumptions have been made:

Unless otherwise specified, the calendars and pricing used at the time of calculating the backtest are assumed to reflect those available at the time. Also, where a price is not available on a historic Pricing Day, the price from the immediately preceding Pricing Day is used.

If a Synthetic High Low Level Change Date is specified, the High Close and Low Close values for the Index Constituents prior to such date are derived using the formulae outlined in Appendix III: Synthetic High/Low Levels.

Before the Snap Switch Date, High Snap for the Constituent $i$, on Index Business Day $t$ refers to the High Close for the Constituent $i$, on Index Business Day $t$; Low Snap for the Constituent $i$, on Index Business Day $t$ refers to the Low Close for the Constituent $i$, on Index Business Day $t$.

## Section 5: Stakeholder engagement, risk, and limitations

## Limitations of the index

Though the Index is designed to be representative of the markets it measures or otherwise aligns with its stated objective, it may not be representative in every case or achieve its stated objective in all instances. It is designed and calculated strictly to follow the rules of this Methodology, and any Index level or other output is limited in its usefulness to such design and calculation.

Markets can be volatile, including those market interests that the Index measures or upon which the Index is dependent to achieve its stated objective. For example, illiquidity can have an impact on the quality or amount of data available to the administrator for calculation and may cause the Index to produce unpredictable or unanticipated results.

In addition, changes to the availability and/or accuracy of trade, liquidity or price data, may render the objective of the Index unachievable or to become impractical to replicate by investors. They are for the indicative purpose.

In particular, the Index measures the performance of a weighted portfolio of instruments. The Indices are therefore subject to the effectiveness of such investment strategy.

Bloomberg Versa Indices Methodology

26

## Bloomberg Versa Indices Methodology

## Section 6: Benchmark oversight and governance

## Benchmark governance, audit, and review structure

Please refer to the BISL Benchmark Procedures Handbook available here.

## Index and Methodology Changes

Please refer to the BISL Benchmark Procedures Handbook available here.

## Expert judgement and Discretion

Please refer to the BISL Benchmark Procedures Handbook available here.

## Conflicts of interest

Please refer to the BISL Benchmark Procedures Handbook available here.

## Restatement policy

Please refer to the BISL Benchmark Procedures Handbook available here.

## Cessation Policy

Please refer to the BISL Benchmark Procedures Handbook available here.

Bloomberg Versa Indices Methodology

## March 21, 2025

27

## Bloomberg Versa Indices Methodology

## March 21, 2025

## Appendix I: Glossary for All Sections

Market Disruption Event

A situation wherein markets cease to function in a regular manner. See Appendix II: Market Disruptions.

Bloomberg Versa Indices Methodology

28

## Bloomberg Versa Indices Methodology

## Appendix II: Market Disruptions

Please refer to the BISL Benchmark Procedures Handbook available here.

Bloomberg Versa Indices Methodology

## March 21, 2025

29

## Bloomberg Versa Indices Methodology

## March 21, 2025

## Appendix III: Synthetic High/Lows Levels

To produce historical high/low values, the below calculation framework is used to translate available adjusted high/low values from a Base Index to a Target Index.

The synthetic high/low values are calculated for the Target Index, for each Index Business Day, t, using the following formulae:

$$
HighTarget_t = CloseTarget_t * (1 + HighBaseRet_t \times Beta(CloseTargetRet_{t-l+1,t}, CloseBaseRet_{t-l+1,t})) \quad (1)
$$

$$
LowTarget_t = CloseTarget_t * (1 + LowBaseRet_t \times Beta(CloseTargetRet_{t-l+1,t}, CloseBaseRet_{t-l+1,t})) \quad (2)
$$

Where, with respect to the Base Index:

$$
CloseBaseRet_t = (CloseBase_t / CloseBase_{t-1}) - 1 \quad (3)
$$

$$
HighBaseRet_t = (HighBase_t / CloseBase_t) - 1 \quad (4)
$$

$$
LowBaseRet_t = (LowBase_t / CloseBase_t) - 1 \qquad (5)
$$

Where, with respect to the Target Index:

$$
CloseTargetRet_t = (CloseTarget_t / CloseTarget_{t-1}) - 1 \quad (6)
$$

And:

Where:

$$
Beta(CloseTargetRet_{t-l+1,t}, CloseBaseRet_{t-l+1,t}) = \frac{Cov(CloseTargetRet_{t-l+1,t}, CloseBaseRet_{t-l+1,t})}{Var(CloseBaseRet_{t-l,t})} \quad (7)
$$

$$
\begin{gather*}
Cov(CloseTargetRet_{t-l+1,t}, CloseBaseRet_{t-l+1,t}) = \\
\frac{1}{l-1} \sum_{i=0}^{l-1} (CloseTargetRet_{t-i} - \overline{CloseTargetRet_{t-l+1,t}})(CloseBaseRet_{t-i} - \overline{CloseBaseRet_{t-l+1,t}})
\end{gather*}
\tag{8}
$$

$$
\mathrm{Var}(\mathrm{CloseBaseRet}_{t-l+1,t}) = \frac{1}{l-1} \sum_{i=0}^{l-1} (\mathrm{CloseBaseRet}_{t-i} - \overline{\mathrm{CloseBaseRet}_{t-l+1,t}})^2 \quad (9)
$$

$$
\overline{\text{CloseTargetRet}_{t-l+1,t}} = \frac{1}{l} \sum_{k=0}^{l-1} \text{CloseTargetRet}_{t-k} \qquad (10)
$$

$$
\overline{\text{CloseBaseRet}_{t-l+1,t}} = \frac{1}{l} \sum_{k=0}^{l-1} \text{CloseBaseRet}_{t-k} \qquad (11)
$$

Bloomberg Versa Indices Methodology

30

## Bloomberg Versa Indices Methodology

## March 21, 2025

t - 1 means the Index Business Day immediately preceding t;

$t-l+1$ and $t-k$ means the $(l-1)$th and $k$-th Index Business Day immediately preceding $t$ respectively;

Base Index means the index in which historical high/low prices are available as well as the close index levels;

Target Index means the index in which historical high/low prices are not available but the close index levels are available;

$CloseBase_t$ and $CloseBase_{t-1}$ means the close values that are corporate actions adjusted for the Base Index on Index Business Day $t$ and Index Business Day $t-1$ respectively;

$CloseTarget_t$ and $CloseTarget_{t-1}$ means the close values that are corporate actions adjusted for the Target Index on Index Business Day $t$ and the Target Index on Index Business Day $t-1$ respectively;

$HighBase_t$ means the high values that are corporate actions adjusted for the Base Index on Index Business Day $t$;

LowBase$_{t}$ means the low values that are corporate actions adjusted for the Base Index on Index Business Day t;

l means beta lookback windows, which is set as 252.

Bloomberg Versa Indices Methodology

31

## Bloomberg Versa Indices Methodology

## Appendix IV: ESG Disclosures

## March 21, 2025

## EXPLANATION OF HOW ESG FACTORS ARE REFLECTED IN THE KEY ELEMENTS OF THE BENCHMARK METHODOLOGY

1. Name of the benchmark administrator.

Bloomberg Index Services Limited ("BISL")

2. Type of benchmark

Other Benchmark

3. Name of the benchmark or family of benchmarks.

Bloomberg Versa Indices

4. Does the benchmark methodology for the benchmark or family of benchmarks take into account ESG factors?

No

5. Where the response to Item 4 is positive, please list below, for each family of benchmarks, those ESG factors that are taken into account in the benchmark methodology, taking into account the ESG factors listed in Annex II to Delegated Regulation (EU) 2020/1816.

Please explain how those ESG factors are used for the selection, weighting or exclusion of underlying assets.

The ESG factors shall be disclosed at an aggregated weighted average value at the level of the family of benchmarks.

<table><tr><td>a) List of environmental factors considered:</td><td>Selection, weighting or exclusion:<br/>N/A</td></tr><tr><td>b) List of social factors considered:</td><td>Selection, weighting or exclusion:<br/>N/A</td></tr><tr><td>c) List of governance factors considered:</td><td>Selection, weighting or exclusion:<br/>N/A</td></tr></table>

6. Where the response to Item 4 is positive, please list below, for each benchmark, those ESG factors that are taken into account in the benchmark methodology, taking into account the ESG factors listed in Annex II to Delegated Regulation (EU) 2020/1816, depending on the relevant underlying asset concerned.

Please explain how those ESG factors are used for the selection, weighting or exclusion of underlying assets.

The ESG factors shall not be disclosed for each constituent of the benchmark, but shall be disclosed at an aggregated weighted average value of the benchmark.

Alternatively, all of this information may be provided in the form of a hyperlink to a website of the benchmark administrator included in this explanation. The information on the website shall be easily available and accessible. Benchmark administrators shall ensure that information published on their website remains available for five years

<table>
  <tr>
    <td>a) List of environmental factors considered:</td>
    <td>Selection, weighting or exclusion:<br><br>N/A</td>
  </tr>
  <tr>
    <td>b) List of social factors considered:</td>
    <td>Selection, weighting or exclusion:<br><br>N/A</td>
  </tr>
</table>

Bloomberg Versa Indices Methodology

32

## Bloomberg Versa Indices Methodology

## March 21, 2025

<table>
  <tr>
    <td>c) List of governance factors considered:</td>
    <td>Selection, weighting or exclusion:<br><br>N/A</td>
  </tr>
  <tr>
    <td><b>7.</b> Data and standards used.</td>
    <td></td>
  </tr>
  <tr>
    <td>a) Data input.<br><br><i>(i) Describe whether the data are reported, modelled or, sourced internally or externally.</i><br><br><i>(ii) Where the data are reported, modelled or sourced externally, please name the third party data provider.</i></td>
    <td>N/A</td>
  </tr>
  <tr>
    <td>b) Verification of data and guaranteeing the quality of those data.<br><br><i>Describe how data are verified and how the quality of those data is ensured.</i></td>
    <td>N/A</td>
  </tr>
  <tr>
    <td>c) Reference standards<br><br><i>Describe the international standards used in the benchmark methodology.</i></td>
    <td>N/A</td>
  </tr>
  <tr>
    <td><b>Date on which information has been last updated and reason for the update:</b></td>
    <td>March 21, 2025<br><br>First Publication</td>
  </tr>
</table>

Bloomberg Versa Indices Methodology

33

## Bloomberg Versa Indices Methodology

## March 21, 2025

## Disclaimer

BLOOMBERG, BLOOMBERG INDICES, Bloomberg Versa Indices (the "Indices") are trademarks or service marks of Bloomberg Finance L.P. Bloomberg Finance L.P. and its affiliates, including Bloomberg Index Services Limited, the administrator of the Indices (collectively, "Bloomberg") or Bloomberg's licensors own all proprietary rights in the Indices. Bloomberg does not guarantee the timeliness, accuracy or completeness of any data or information relating to the Indices. Bloomberg makes no warranty, express or implied, as to the Indices or any data or values relating thereto or results to be obtained therefrom, and expressly disclaims all warranties of merchantability and fitness for a particular purpose with respect thereto. It is not possible to invest directly in an Index. Back-tested performance is not actual performance. Past performance is not an indication of future results. To the maximum extent allowed by law, Bloomberg, its licensors, and its and their respective employees, contractors, agents, suppliers and vendors shall have no liability or responsibility whatsoever for any injury or damages - whether direct, indirect, consequential, incidental, punitive or otherwise - arising in connection with the Indices or any data or values relating thereto - whether arising from their negligence or otherwise. This document constitutes the provision of factual information, rather than financial product advice. Nothing in the Indices shall constitute or be construed as an offering of financial instruments or as investment advice or investment recommendations (i.e., recommendations as to whether or not to "buy", "sell", "hold", or to enter or not to enter into any other transaction involving any specific interest or interests) by Bloomberg or a recommendation as to an investment or other strategy by Bloomberg. Data and other information available via the Indices should not be considered as information sufficient upon which to base an investment decision. All information provided by the Indices is impersonal and not tailored to the needs of any person, entity or group of persons. Bloomberg does not express an opinion on the future or expected value of any security or other interest and do not explicitly or implicitly recommend or suggest an investment strategy of any kind. Customers should consider obtaining independent advice before making any financial decisions. © 2025 Bloomberg. All rights reserved. This document and its contents may not be forwarded or redistributed without the prior consent of Bloomberg.

The BLOOMBERG TERMINAL service and Bloomberg data products (the “Services”) are owned and distributed by Bloomberg Finance L.P. (“BFLP”) except (i) in Argentina, Australia and certain jurisdictions in the Pacific islands, Bermuda, China, India, Japan, Korea and New Zealand, where Bloomberg L.P. and its subsidiaries distribute these products, and (ii) in Singapore and the jurisdictions serviced by Bloomberg’s Singapore office, where a subsidiary of BFLP distributes these products.

Bloomberg Index Services Limited is registered in England and Wales under registered number 08934023 and has its registered office at 3 Queen Victoria Street, London, England, EC4N 4TQ. Bloomberg Index Services Limited is authorised and regulated by the Financial Conduct Authority as a benchmark administrator.

<table>
  <tr>
    <td rowspan="6">Take the next step.<br>For additional information,<br>please contact the Bloomberg<br>Help Desk or log into the<br>Customer Service Center at<br><a href="https://service.bloomberg.com">https://service.bloomberg.com</a><br><b>bloomberg.com/indices</b></td>
    <td><b>Beijing</b></td>
    <td><b>Hong Kong</b></td>
    <td><b>New York</b></td>
    <td><b>Singapore</b></td>
  </tr>
  <tr>
    <td>+86 10 6649 7500</td>
    <td>+852 2977 6000</td>
    <td>+1 212 318 2000</td>
    <td>+65 6212 1000</td>
  </tr>
  <tr>
    <td><b>Dubai</b></td>
    <td><b>London</b></td>
    <td><b>San Francisco</b></td>
    <td><b>Sydney</b></td>
  </tr>
  <tr>
    <td>+971 4 364 1000</td>
    <td>+44 20 7330 7500</td>
    <td>+1 415 912 2960</td>
    <td>+61 2 9777 8600</td>
  </tr>
  <tr>
    <td><b>Frankfurt</b></td>
    <td><b>Mumbai</b></td>
    <td><b>São Paulo</b></td>
    <td><b>Tokyo</b></td>
  </tr>
  <tr>
    <td>+49 69 9204 1210</td>
    <td>+91 22 6120 3600</td>
    <td>+55 11 2395 9000</td>
    <td>+81 3 4565 8900</td>
  </tr>
</table>