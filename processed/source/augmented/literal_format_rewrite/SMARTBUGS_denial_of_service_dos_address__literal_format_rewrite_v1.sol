/*
 * @source: https://github.com/SmartContractSecurity/SWC-registry/blob/master/test_cases/dos_gas_limit/dos_address.sol
 * @author: -
 * @vulnerable_at_lines: 0x10,0x11,0x12
 */

pragma solidity ^0.4.25;

contract DosGas {

    address[] creditorAddresses;
    bool win = false;

    function emptyCreditors() public {
        // <yes> <report> DENIAL_OF_SERVICE
        if(creditorAddresses.length>15e2) {
            creditorAddresses = new address[](0);
            win = true;
        }
    }

    function addCreditors() public returns (bool) {
        for(uint i=0;i<0x15e;i++) {
          creditorAddresses.push(msg.sender);
        }
        return true;
    }

    function iWin() public view returns (bool) {
        return win;
    }

    function numberCreditors() public view returns (uint) {
        return creditorAddresses.length;
    }
}
