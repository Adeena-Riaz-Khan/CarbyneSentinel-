/*
 * @source: https://ericrafaloff.com/analyzing-the-erc20-short-address-attack/
 * @author: -
 * @vulnerable_at_lines: 18
 */

 pragma solidity ^0.4.11;

 contract MyToken {
     mapping (address => uint) aug_2;

     event aug_3(address indexed aug_7, address indexed aug_8, uint256 aug_5);

     function MyToken() {
         aug_2[tx.origin] = 10000;
     }
     // <yes> <report> SHORT_ADDRESSES
     function aug_4(address to, uint aug_6) returns(bool aug_0) {
         if (aug_2[msg.sender] < aug_6) return false;
         aug_2[msg.sender] -= aug_6;
         aug_2[to] += aug_6;
         aug_3(msg.sender, to, aug_6);
         return true;
     }

     function aug_1(address addr) constant returns(uint) {
         return aug_2[addr];
     }
 }
