// SPDX-License-Identifier: UNLICENSED
/*
 * @source: https://github.com/seresistvanandras/EthBench/blob/master/Benchmark/Simple/reentrant.sol
 * @author: -
 * @vulnerable_at_lines: 21
 */

pragma solidity ^0.8.30;

contract EtherBank {
    mapping(address => uint) userBalances;

    function getBalance(address user) public view returns (uint) {
        return userBalances[user];
    }

    function addToBalance() public payable {
        userBalances[msg.sender] += msg.value;
    }

    function withdrawBalance() public {
        uint amountToWithdraw = userBalances[msg.sender];
        (bool success, ) = msg.sender.call{value: amountToWithdraw}("");
        if (!success) {
            revert();
        }
        userBalances[msg.sender] = 0;
    }
}
