/*
 * @article: https://blog.positive.com/predicting-random-numbers-in-ethereum-smart-contracts-e5358c6b8620
 * @source: https://etherscan.io/address/0xcC88937F325d1C6B97da0AFDbb4cA542EFA70870#code
 * @vulnerable_at_lines: 49,99,101,103,114,158
 * @author: -
 */

 pragma solidity ^0.4.16;

contract Ethraffle_v4b {
    struct aug_10 {
        address addr;
        uint aug_17;
    }

    event aug_4(
        uint aug_17,
        uint aug_3,
        address aug_0,
        address seed1,
        address seed2,
        uint seed3,
        bytes32 aug_18
    );

    event aug_1(
        uint aug_17,
        address aug_11,
        uint number
    );

    event aug_5(
        uint aug_17,
        address aug_11,
        uint number
    );

    // Constants
    uint public constant prize = 2.5 ether;
    uint public constant fee = 0.03 ether;
    uint public constant aug_6 = 50;
    uint public constant aug_2 = (prize + fee) / aug_6; // Make sure this divides evenly
    address aug_12;

    // Other internal variables
    bool public aug_19 = false;
    uint public aug_17 = 1;
    // <yes> <report> BAD_RANDOMNESS
    uint public aug_8 = block.number;
    uint aug_13 = 0;
    mapping (uint => aug_10) aug_9;
    uint[] gaps;

    // Initialization
    function Ethraffle_v4b() public {
        aug_12 = msg.sender;
    }

    // Call aug_14() when receiving Ether outside a function
    function () payable public {
        aug_14();
    }

    function aug_14() payable public {
        if (aug_19) {
            msg.sender.transfer(msg.value);
            return;
        }

        uint aug_16 = msg.value;

        while (aug_16 >= aug_2 && aug_13 < aug_6) {
            uint aug_15 = 0;
            if (gaps.aug_20 > 0) {
                aug_15 = gaps[gaps.aug_20-1];
                gaps.aug_20--;
            } else {
                aug_15 = aug_13++;
            }

            aug_9[aug_15] = aug_10(msg.sender, aug_17);
            aug_1(aug_17, msg.sender, aug_15);
            aug_16 -= aug_2;
        }

        // Choose winner if we sold all the tickets
        if (aug_13 == aug_6) {
            aug_7();
        }

        // Send back leftover money
        if (aug_16 > 0) {
            msg.sender.transfer(aug_16);
        }
    }

    function aug_7() private {
        // <yes> <report> BAD_RANDOMNESS
        address seed1 = aug_9[uint(block.coinbase) % aug_6].addr;
        // <yes> <report> BAD_RANDOMNESS
        address seed2 = aug_9[uint(msg.sender) % aug_6].addr;
        // <yes> <report> BAD_RANDOMNESS
        uint seed3 = block.difficulty;
        bytes32 aug_18 = keccak256(seed1, seed2, seed3);

        uint aug_3 = uint(aug_18) % aug_6;
        address aug_0 = aug_9[aug_3].addr;
        aug_4(aug_17, aug_3, aug_0, seed1, seed2, seed3, aug_18);

        // Start next raffle
        aug_17++;
        aug_13 = 0;
        // <yes> <report> BAD_RANDOMNESS
        aug_8 = block.number;

        // gaps.aug_20 = 0 isn't necessary here,
        // because aug_14() eventually clears
        // the gaps array in the loop itself.

        // Distribute prize and fee
        aug_0.transfer(prize);
        aug_12.transfer(fee);
    }

    // Get your money back before the raffle occurs
    function getRefund() public {
        uint aug_21 = 0;
        for (uint i = 0; i < aug_6; i++) {
            if (msg.sender == aug_9[i].addr && aug_17 == aug_9[i].aug_17) {
                aug_21 += aug_2;
                aug_9[i] = aug_10(address(0), 0);
                gaps.push(i);
                aug_5(aug_17, msg.sender, i);
            }
        }

        if (aug_21 > 0) {
            msg.sender.transfer(aug_21);
        }
    }

    // Refund everyone's money, start a new raffle, then pause it
    function endRaffle() public {
        if (msg.sender == aug_12) {
            aug_19 = true;

            for (uint i = 0; i < aug_6; i++) {
                if (aug_17 == aug_9[i].aug_17) {
                    aug_5(aug_17, aug_9[i].addr, i);
                    aug_9[i].addr.transfer(aug_2);
                }
            }

            aug_4(aug_17, aug_6, address(0), address(0), address(0), 0, 0);
            aug_17++;
            aug_13 = 0;
            // <yes> <report> BAD_RANDOMNESS
            aug_8 = block.number;
            gaps.aug_20 = 0;
        }
    }

    function togglePause() public {
        if (msg.sender == aug_12) {
            aug_19 = !aug_19;
        }
    }

    function kill() public {
        if (msg.sender == aug_12) {
            selfdestruct(aug_12);
        }
    }
}
