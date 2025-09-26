// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

// src/campaign/interfaces/IBaseNudgeCampaign.sol

interface IBaseNudgeCampaign {
    // Errors
    error CampaignPaused();
    error UnauthorizedSwapCaller();
    error Unauthorized();
    error InsufficientAmountReceived();
    error InvalidToTokenReceived(address toToken);

    // Enums
    enum ParticipationStatus {
        PARTICIPATING,
        INVALIDATED,
        CLAIMED,
        HANDLED_OFFCHAIN
    }

    // Structs
    struct Participation {
        ParticipationStatus status;
        address userAddress;
        uint256 toAmount;
        uint256 rewardAmount;
        uint256 startTimestamp;
        uint256 startBlockNumber;
    }

    // Events
    event NewParticipation(
        uint256 indexed campaignId,
        address indexed userAddress,
        uint256 pID,
        uint256 toAmount,
        uint256 entitledRewards,
        uint256 fees,
        bytes data
    );

    // External functions
    function handleReallocation(
        uint256 campaignId,
        address userAddress,
        address toToken,
        uint256 toAmount,
        bytes memory data
    ) external payable;

    // View functions
    function getBalanceOfSelf(address token) external view returns (uint256);
}

