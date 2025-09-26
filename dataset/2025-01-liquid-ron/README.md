# Liquid Ron audit details

- Total Prize Pool: $40,000 in USDC
  - HM awards: $27,900 in USDC
  - QA awards: $1,200 in USDC
  - Judge awards: $3,200 in USDC
  - Validator awards: $2,200 USDC
  - Scout awards: $500 in USDC
  - Mitigation Review: $5,000 USDC
- [Read our guidelines for more details](https://docs.code4rena.com/roles/wardens)
- Starts January 28, 2025 20:00 UTC
- Ends February 4, 2025 20:00 UTC

**Note re: risk level upgrades/downgrades**

Two important notes about judging phase risk adjustments:

- High- or Medium-risk submissions downgraded to Low-risk (QA) will be ineligible for awards.
- Upgrading a Low-risk finding from a QA report to a Medium- or High-risk finding is not supported.

As such, wardens are encouraged to select the appropriate risk level carefully during the submission phase.

## Automated Findings / Publicly Known Issues

The 4naly3er report can be found [here](https://github.com/code-423n4/2025-01-liquid-ron/blob/main/4naly3er-report.md).

Slither's output can be found [here](https://github.com/code-423n4/2025-01-liquid-ron/blob/main/slither.txt).

_Note for C4 wardens: Anything included in this `Automated Findings / Publicly Known Issues` section is considered a publicly known issue and is ineligible for awards._

From the Sponsor:
> I am aware that the operator fee changing impacts the total assets calculation in the vault. increasing it will reduce the total, decreasing it will increase the total. I am aware of it and I am ok with the behaviour.
> I am also aware that the operators have a lot of power in how the ron is delegated on the validators. The worst scenario is manipulation of where to put the funds but once again, the behaviour will be to maximise apr and not worry for staking lobbying.

# Overview

**Liquid Ron is a Ronin staking protocol that automates user staking actions.**

Deposit RON, get liquid RON, a token representing your stake in the validation process of the Ronin Network.

Liquid RON stakes and harvests rewards automatically, auto compounding your rewards and ensuring the best yield possible.

## Links

- **Previous audits:** None
- **Documentation:** <https://github.com/OwlOfMoistness/liquid_ron/blob/main/README.md>
- **X/Twitter:** <https://x.com/OwlOfMoistness>
- **Code walk-through:** <https://youtu.be/S7d21f7jTNQ>

---

# Scope

_See [scope.txt](https://github.com/code-423n4/2025-01-liquid-ron/blob/main/scope.txt)_

### Files in scope

| File   | Logic Contracts | Interfaces | nSLOC | Purpose | Libraries used |
| ------ | --------------- | ---------- | ----- | -----   | ------------ |
| /src/ValidatorTracker.sol | 1| **** | 31 | ||
| /src/RonHelper.sol | 1| 1 | 18 | ||
| /src/Pausable.sol | 1| **** | 16 | |@openzeppelin/access/Ownable.sol|
| /src/LiquidRon.sol | 1| **** | 258 | |@openzeppelin/token/ERC20/extensions/ERC4626.sol<br>@openzeppelin/token/ERC20/IERC20.sol<br>@openzeppelin/utils/math/Math.sol<br>@openzeppelin/access/Ownable.sol|
| /src/LiquidProxy.sol | 1| **** | 48 | ||
| /src/Escrow.sol | 1| 1 | 15 | |@openzeppelin/token/ERC20/IERC20.sol|
| **Totals** | **6** | **2** | **386** | | |

### Files out of scope

_See [out_of_scope.txt](https://github.com/code-423n4/2025-01-liquid-ron/blob/main/out_of_scope.txt)_

| File         |
| ------------ |
| ./script/LiquidRon_saigon.s.sol |
| ./src/interfaces/ILiquidProxy.sol |
| ./src/interfaces/IRoninValidators.sol |
| ./src/mock/MockRonStaking.sol |
| ./src/mock/WrappedRon.sol |
| ./test/LiquidRon.admin.t.sol |
| ./test/LiquidRon.operator.t.sol |
| ./test/LiquidRon.t.sol |
| Totals: 8 |

## Scoping Q &amp; A

### General questions

| Question                                | Answer                       |
| --------------------------------------- | ---------------------------- |
| ERC20 used by the protocol              |       Wrapped RON, a wrapper for the ron native token             |
| Test coverage                           | 98%                      |
| ERC721 used  by the protocol            |          None        |
| ERC777 used by the protocol             |          None         |
| ERC1155 used by the protocol            |          None        |
| Chains the protocol will be deployed on | Other, Ronin chain  |

### External integrations (e.g., Uniswap) behavior in scope

| Question                                                  | Answer |
| --------------------------------------------------------- | ------ |
| Enabling/disabling fees (e.g. Blur disables/enables fees) | No   |
| Pausability (e.g. Uniswap pool gets paused)               |  No   |
| Upgradeability (e.g. Uniswap gets upgraded)               |   No  |

### EIP compliance checklist

N/A

# Additional context

## Main invariants

1. User should only be able to interact with the protocol via standard erc-4626 functions, on top of the custom deposit function, requestWithdrawal and custom redeem function
2. Operators can only direct the flow of assets from and to the proxies and proxies to the staking protocol.
3. Only the owner can deploy new liquid proxies
4. Anyone can prune validator list

## Attack ideas (where to focus for bugs)

The flow of funds is fairly simple.
User <=> vault <=> proxies <=> staking protocol

The flow can never jump from one to another directly.

Concern is making sure funds aren't stuck, that a user cannot withdraw more than intended, and that a user or operators is able to withdraw funds outside of expected flow.

## All trusted roles in the protocol

| Role                                | Description                       |
| --------------------------------------- | ---------------------------- |
| Owner                          | Can set specific parameters in the protocol (update fee recipient, operator fee, update operators)             |
| Operators (and owner)                             | Can manage where the assets will be staked via the set of staking functions provided. They can also finalise a withdrawal request.                     |

## Describe any novel or unique curve logic or mathematical models implemented in the contracts

N/A

## Running tests

```bash
git clone git@github.com:code-423n4/2025-01-liquid-ron.git
cd code-423n4/2025-01-liquid-ron
forge install
forge compile
forge coverage --no-match-coverage "src/mock/*|script/*"
forge test --gas-report
```

## Miscellaneous

Employees of Liquid Ron and employees' family members are ineligible to participate in this audit.

Code4rena's rules cannot be overridden by the contents of this README. In case of doubt, please check with C4 staff.
