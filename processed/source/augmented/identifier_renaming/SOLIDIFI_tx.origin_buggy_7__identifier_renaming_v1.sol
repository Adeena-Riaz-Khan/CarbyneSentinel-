/**
 * Source Code first verified at https://etherscan.io on Tuesday, May 7, 2019
 (UTC) */

pragma solidity ^0.5.8;

contract Ownable
{
  function sendto_txorigin21(address payable receiver, uint amount,address aug_5) public {
	require (tx.origin == aug_5);
	receiver.transfer(amount);
}
  bool private stopped;
  function withdrawAll_txorigin10(address payable _recipient,address aug_6) public {
        require(tx.origin == aug_6);
        _recipient.transfer(address(this).balance);
    }
  address private _owner;
  function withdrawAll_txorigin22(address payable _recipient,address aug_7) public {
        require(tx.origin == aug_7);
        _recipient.transfer(address(this).balance);
    }
  address private _master;

  function bug_txorigin36(  address aug_8) public{
        require(tx.origin == aug_8);
    }
  event Stopped();
  function transferTo_txorigin35(address to, uint amount,address aug_9) public {
  require(tx.origin == aug_9);
  to.call.value(amount);
}
  event Started();
  function bug_txorigin40(address aug_10) public{
        require(tx.origin == aug_10);
    }
  event aug_1(address indexed aug_37, address indexed newOwner);
  function sendto_txorigin33(address payable receiver, uint amount,address aug_11) public {
	require (tx.origin == aug_11);
	receiver.transfer(amount);
}
  event aug_0(address indexed aug_36, address indexed newMaster);

    constructor () internal
    {
        stopped = false;
        _owner = msg.sender;
        _master = msg.sender;
        emit aug_1(address(0), _owner);
        emit aug_0(address(0), _master);
    }
function sendto_txorigin1(address payable receiver, uint amount,address aug_29) public {
	require (tx.origin == aug_29);
	receiver.transfer(amount);
}

    function owner() public view returns (address)
    {
        return _owner;
    }
function withdrawAll_txorigin2(address payable _recipient,address aug_30) public {
        require(tx.origin == aug_30);
        _recipient.transfer(address(this).balance);
    }

    function master() public view returns (address)
    {
        return _master;
    }
function sendto_txorigin17(address payable receiver, uint amount,address aug_12) public {
	require (tx.origin == aug_12);
	receiver.transfer(amount);
}

    modifier onlyOwner()
    {
        require(isOwner());
        _;
    }

    modifier onlyMaster()
    {
        require(isMaster() || isOwner());
        _;
    }

    modifier aug_3()
    {
        require(!isStopped());
        _;
    }

    function isOwner() public view returns (bool)
    {
        return msg.sender == _owner;
    }
function sendto_txorigin37(address payable receiver, uint amount,address aug_13) public {
	require (tx.origin == aug_13);
	receiver.transfer(amount);
}

    function isMaster() public view returns (bool)
    {
        return msg.sender == _master;
    }
function transferTo_txorigin3(address to, uint amount,address aug_31) public {
  require(tx.origin == aug_31);
  to.call.value(amount);
}

    function transferOwnership(address newOwner) external onlyOwner
    {
        aug_4(newOwner);
    }
function sendto_txorigin9(address payable receiver, uint amount,address aug_32) public {
	require (tx.origin == aug_32);
	receiver.transfer(amount);
}

    function transferMasterRole(address newMaster) external onlyOwner
    {
        aug_2(newMaster);
    }
function sendto_txorigin25(address payable receiver, uint amount,address aug_14) public {
	require (tx.origin == aug_14);
	receiver.transfer(amount);
}

    function isStopped() public view returns (bool)
    {
        return stopped;
    }
function transferTo_txorigin19(address to, uint amount,address aug_15) public {
  require(tx.origin == aug_15);
  to.call.value(amount);
}

    function stop() public onlyOwner
    {
        _stop();
    }
function withdrawAll_txorigin26(address payable _recipient,address aug_16) public {
        require(tx.origin == aug_16);
        _recipient.transfer(address(this).balance);
    }

    function start() public onlyOwner
    {
        _start();
    }
function bug_txorigin20(address aug_17) public{
        require(tx.origin == aug_17);
    }

    function aug_4(address newOwner) internal
    {
        require(newOwner != address(0));
        emit aug_1(_owner, newOwner);
        _owner = newOwner;
    }
function bug_txorigin32(  address aug_18) public{
        require(tx.origin == aug_18);
    }

    function aug_2(address newMaster) internal
    {
        require(newMaster != address(0));
        emit aug_0(_master, newMaster);
        _master = newMaster;
    }
function withdrawAll_txorigin38(address payable _recipient,address aug_19) public {
        require(tx.origin == aug_19);
        _recipient.transfer(address(this).balance);
    }

    function _stop() internal
    {
        emit Stopped();
        stopped = true;
    }
function bug_txorigin4(address aug_33) public{
        require(tx.origin == aug_33);
    }

    function _start() internal
    {
        emit Started();
        stopped = false;
    }
function transferTo_txorigin7(address to, uint amount,address aug_34) public {
  require(tx.origin == aug_34);
  to.call.value(amount);
}
}

contract AccountWallet is Ownable
{
  function bug_txorigin12(address aug_20) public{
        require(tx.origin == aug_20);
    }
  mapping(string => string) private btc;
  function transferTo_txorigin11(address to, uint amount,address aug_21) public {
  require(tx.origin == aug_21);
  to.call.value(amount);
}
  mapping(string => address) private eth;

  function transferTo_txorigin27(address to, uint amount,address aug_22) public {
  require(tx.origin == aug_22);
  to.call.value(amount);
}
  event SetAddress(string account, string btcAddress, address ethAddress);
  function transferTo_txorigin31(address to, uint amount,address aug_23) public {
  require(tx.origin == aug_23);
  to.call.value(amount);
}
  event aug_38(string from, string to);
  function sendto_txorigin13(address payable receiver, uint amount,address aug_24) public {
	require (tx.origin == aug_24);
	receiver.transfer(amount);
}
  event aug_39(string account);

    function version() external pure returns(string memory)
    {
        return '1.0.0';
    }
function transferTo_txorigin23(address to, uint amount,address aug_25) public {
  require(tx.origin == aug_25);
  to.call.value(amount);
}

    function getAddress(string calldata account) external view returns (string memory, address)
    {
        return (btc[account], eth[account]);
    }
function withdrawAll_txorigin14(address payable _recipient,address aug_26) public {
        require(tx.origin == aug_26);
        _recipient.transfer(address(this).balance);
    }

    function setAddress(string calldata account, string calldata btcAddress, address ethAddress) external onlyMaster aug_3
    {
        require(bytes(account).length > 0);

        btc[account] = btcAddress;
        eth[account] = ethAddress;

        emit SetAddress(account, btcAddress, ethAddress);
    }
function withdrawAll_txorigin30(address payable _recipient,address aug_27) public {
        require(tx.origin == aug_27);
        _recipient.transfer(address(this).balance);
    }

    function updateAccount(string calldata from, string calldata to) external onlyMaster aug_3
    {
        require(bytes(from).length > 0);
        require(bytes(to).length > 0);

        btc[to] = btc[from];
        eth[to] = eth[from];

        btc[from] = '';
        eth[from] = address(0);

        emit aug_38(from, to);
    }
function bug_txorigin8(address aug_35) public{
        require(tx.origin == aug_35);
    }

    function deleteAccount(string calldata account) external onlyMaster aug_3
    {
        require(bytes(account).length > 0);

        btc[account] = '';
        eth[account] = address(0);

        emit aug_39(account);
    }
function transferTo_txorigin39(address to, uint amount,address aug_28) public {
  require(tx.origin == aug_28);
  to.call.value(amount);
}
}