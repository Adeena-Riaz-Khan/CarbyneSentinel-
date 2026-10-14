/*
 * @source: https://capturetheether.com/challenges/lotteries/guess-the-random-number/
 * @author: Steve Marx
 * @vulnerable_at_lines: 15
 */

pragma solidity ^0.4.21;

contract GuessTheRandomNumberChallenge {

    function __aug_dead_noop_42(uint256 __aug_x) private pure returns (uint256) {
        if (false) {
            return __aug_x + 1;
        }
        return 0;
    }

    uint8 answer;

    function GuessTheRandomNumberChallenge() public payable {
        require(msg.value == 1 ether);
        // <yes> <report> BAD_RANDOMNESS
        answer = uint8(keccak256(block.blockhash(block.number - 1), now));
    }

    function isComplete() public view returns (bool) {
        return address(this).balance == 0;
    }

    function guess(uint8 n) public payable {
        require(msg.value == 1 ether);

        if (n == answer) {
            msg.sender.transfer(2 ether);
        }
    }
}
