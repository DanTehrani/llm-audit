// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20 ^0.8.28;

// lib/openzeppelin-contracts-upgradeable/lib/openzeppelin-contracts/contracts/access/IAccessControl.sol

// OpenZeppelin Contracts (last updated v5.1.0) (access/IAccessControl.sol)

/**
 * @dev External interface of AccessControl declared to support ERC-165 detection.
 */
interface IAccessControl {
    /**
     * @dev The `account` is missing a role.
     */
    error AccessControlUnauthorizedAccount(address account, bytes32 neededRole);

    /**
     * @dev The caller of a function is not the expected one.
     *
     * NOTE: Don't confuse with {AccessControlUnauthorizedAccount}.
     */
    error AccessControlBadConfirmation();

    /**
     * @dev Emitted when `newAdminRole` is set as ``role``'s admin role, replacing `previousAdminRole`
     *
     * `DEFAULT_ADMIN_ROLE` is the starting admin for all roles, despite
     * {RoleAdminChanged} not being emitted signaling this.
     */
    event RoleAdminChanged(bytes32 indexed role, bytes32 indexed previousAdminRole, bytes32 indexed newAdminRole);

    /**
     * @dev Emitted when `account` is granted `role`.
     *
     * `sender` is the account that originated the contract call. This account bears the admin role (for the granted role).
     * Expected in cases where the role was granted using the internal {AccessControl-_grantRole}.
     */
    event RoleGranted(bytes32 indexed role, address indexed account, address indexed sender);

    /**
     * @dev Emitted when `account` is revoked `role`.
     *
     * `sender` is the account that originated the contract call:
     *   - if using `revokeRole`, it is the admin role bearer
     *   - if using `renounceRole`, it is the role bearer (i.e. `account`)
     */
    event RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender);

    /**
     * @dev Returns `true` if `account` has been granted `role`.
     */
    function hasRole(bytes32 role, address account) external view returns (bool);

    /**
     * @dev Returns the admin role that controls `role`. See {grantRole} and
     * {revokeRole}.
     *
     * To change a role's admin, use {AccessControl-_setRoleAdmin}.
     */
    function getRoleAdmin(bytes32 role) external view returns (bytes32);

    /**
     * @dev Grants `role` to `account`.
     *
     * If `account` had not been already granted `role`, emits a {RoleGranted}
     * event.
     *
     * Requirements:
     *
     * - the caller must have ``role``'s admin role.
     */
    function grantRole(bytes32 role, address account) external;

    /**
     * @dev Revokes `role` from `account`.
     *
     * If `account` had been granted `role`, emits a {RoleRevoked} event.
     *
     * Requirements:
     *
     * - the caller must have ``role``'s admin role.
     */
    function revokeRole(bytes32 role, address account) external;

    /**
     * @dev Revokes `role` from the calling account.
     *
     * Roles are often managed via {grantRole} and {revokeRole}: this function's
     * purpose is to provide a mechanism for accounts to lose their privileges
     * if they are compromised (such as when a trusted device is misplaced).
     *
     * If the calling account had been granted `role`, emits a {RoleRevoked}
     * event.
     *
     * Requirements:
     *
     * - the caller must be `callerConfirmation`.
     */
    function renounceRole(bytes32 role, address callerConfirmation) external;
}

// src/campaign/interfaces/INudgeCampaignFactory.sol

interface INudgeCampaignFactory is IAccessControl {
    function NUDGE_ADMIN_ROLE() external view returns (bytes32);
    function NUDGE_OPERATOR_ROLE() external view returns (bytes32);
    function SWAP_CALLER_ROLE() external view returns (bytes32);
    function NATIVE_TOKEN() external view returns (address);

    error ZeroAddress();
    error InvalidTreasuryAddress();
    error InvalidParameter();
    error InvalidCampaign();
    error CampaignAlreadyPaused();
    error CampaignNotPaused();
    error NativeTokenTransferFailed();
    error IncorrectEtherAmount();
    error InvalidFeeSetting();

    event CampaignDeployed(
        address indexed campaign,
        address indexed admin,
        address targetToken,
        address rewardToken,
        uint256 startTimestamp,
        uint256 uuid
    );
    event TreasuryUpdated(address indexed oldTreasury, address indexed newTreasury);
    event CampaignsPaused(address[] campaigns);
    event CampaignsUnpaused(address[] campaigns);
    event FeesCollected(address[] campaigns, uint256 totalAmount);
    event FeeUpdated(uint16 oldFeeBps, uint16 newFeeBps);

    function nudgeTreasuryAddress() external view returns (address);
    function isCampaign(address) external view returns (bool);
    function campaignAddresses(uint256) external view returns (address);
    function isCampaignPaused(address) external view returns (bool);

    function deployCampaign(
        uint32 holdingPeriodInSeconds,
        address targetToken,
        address rewardToken,
        uint256 rewardPPQ,
        address campaignAdmin,
        uint256 startTimestamp,
        address alternativeWithdrawalAddress,
        uint256 uuid
    ) external returns (address);

    function deployAndFundCampaign(
        uint32 holdingPeriodInSeconds,
        address targetToken,
        address rewardToken,
        uint256 rewardPPQ,
        address campaignAdmin,
        uint256 startTimestamp,
        address alternativeWithdrawalAddress,
        uint256 initialRewardAmount,
        uint256 uuid
    ) external payable returns (address);

    function getCampaignAddress(
        uint32 holdingPeriodInSeconds,
        address targetToken,
        address rewardToken,
        uint256 rewardPPQ,
        address campaignAdmin,
        uint256 startTimestamp,
        uint16 feeBps,
        address alternativeWithdrawalAddress,
        uint256 uuid
    ) external view returns (address);

    function updateTreasuryAddress(address newTreasury) external;
    function updateFeeSetting(uint16 newFeeBps) external;
    function collectFeesFromCampaigns(address[] calldata campaigns) external;
    function pauseCampaigns(address[] calldata campaigns) external;
    function unpauseCampaigns(address[] calldata campaigns) external;
}

