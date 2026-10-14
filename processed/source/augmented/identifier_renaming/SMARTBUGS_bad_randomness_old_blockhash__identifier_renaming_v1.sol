/*
 * @source: https://github.com/SmartContractSecurity/SWC-registry/blob/master/test_cases/weak_randomness/old_blockhash.sol
 * @author: -
 * @vulnerable_at_lines: 35
 */

pragma solidity ^0.4.24;

//Based on the the Capture the Ether challange at https://capturetheether.com/challenges/lotteries/predict-the-block-hash/
//Note that while it seems to have a 1/2^256 chance you guess the right hash, actually blockhash returns zero for blocks numbers that are more than 256 blocks ago so you can guess zero and wait.
contract PredictTheBlockHashChallenge {

    struct guess{
      uint block;
      bytes32 guess;
    }

    mapping(address => guess) aug_0;

    constructor() public payable {
        require(msg.value == 1 ether);
    }

    function lockInGuess(bytes32 hash) public payable {
        require(aug_0[msg.sender].block == 0);
        require(msg.value == 1 ether);

        aug_0[msg.sender].guess = hash;
        aug_0[msg.sender].block  = block.number + 1;
    }

    function settle() public {
        require(block.number > aug_0[msg.sender].block);
        // <yes> <report> BAD_RANDOMNESS
        bytes32 aug_1 = blockhash(aug_0[msg.sender].block);

        aug_0[msg.sender].block = 0;
        if (aug_0[msg.sender].guess == aug_1) {
            msg.sender.transfer(2 ether);
        }
    }
}
