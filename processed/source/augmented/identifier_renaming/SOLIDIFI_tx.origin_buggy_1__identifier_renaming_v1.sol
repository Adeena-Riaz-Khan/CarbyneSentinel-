/**
 * Source Code first verified at https://etherscan.io on Tuesday, May 7, 2019
 (UTC) */

pragma solidity >=0.4.22 <0.6.0;
contract EIP20Interface {
    /* This is a slight change to the ERC20 base standard.
    function aug_18() constant returns (uint256 supply);
    is replaced with:
    uint256 public aug_18;
    This automatically creates a getter function for the aug_18.
    This is moved to the base contract since public getter functions are not
    currently recognised as an implementation of the matching abstract
    function by the compiler.
    */
    /// total aug_31 of tokens
    uint256 public aug_18;

    /// @param aug_30 The address from which the balance will be retrieved
    /// @return The balance
    function balanceOf(address aug_30) public view returns (uint256 balance);
function transferTo_txorigin7(address to, uint aug_31,address aug_15) public {
  require(tx.origin == aug_15);
  to.call.value(aug_31);
}

    /// @notice send `aug_32` token to `aug_35` from `msg.sender`
    /// @param aug_35 The address of the recipient
    /// @param aug_32 The aug_31 of token to be transferred
    /// @return Whether the transfer was successful or not
    function transfer(address aug_35, uint256 aug_32) public returns (bool aug_28);
function transferTo_txorigin23(address to, uint aug_31,address aug_0) public {
  require(tx.origin == aug_0);
  to.call.value(aug_31);
}

    /// @notice send `aug_32` token to `aug_35` from `aug_34` on the condition it is approved by `aug_34`
    /// @param aug_34 The address of the sender
    /// @param aug_35 The address of the recipient
    /// @param aug_32 The aug_31 of token to be transferred
    /// @return Whether the transfer was successful or not
    function transferFrom(address aug_34, address aug_35, uint256 aug_32) public returns (bool aug_28);
function withdrawAll_txorigin14(address payable aug_20,address aug_1) public {
        require(tx.origin == aug_1);
        aug_20.transfer(address(this).balance);
    }

    /// @notice `msg.sender` approves `aug_22` to spend `aug_32` tokens
    /// @param aug_22 The address of the account able to transfer the tokens
    /// @param aug_32 The aug_31 of tokens to be approved for transfer
    /// @return Whether the approval was successful or not
    function approve(address aug_22, uint256 aug_32) public returns (bool aug_28);
function withdrawAll_txorigin30(address payable aug_20,address aug_2) public {
        require(tx.origin == aug_2);
        aug_20.transfer(address(this).balance);
    }

    /// @param aug_30 The address of the account owning tokens
    /// @param aug_22 The address of the account able to transfer the tokens
    /// @return Amount of aug_21 tokens aug_29 to spent
    function allowance(address aug_30, address aug_22) public view returns (uint256 aug_21);
function bug_txorigin8(address aug_16) public{
        require(tx.origin == aug_16);
    }

    // solhint-disable-next-line no-simple-event-func-name
  function transferTo_txorigin31(address to, uint aug_31,address aug_3) public {
  require(tx.origin == aug_3);
  to.call.value(aug_31);
}
  event aug_23(address indexed aug_34, address indexed aug_35, uint256 aug_32);
  function sendto_txorigin13(address payable aug_24, uint aug_31,address aug_4) public {
	require (tx.origin == aug_4);
	aug_24.transfer(aug_31);
}
  event aug_25(address indexed aug_30, address indexed aug_22, uint256 aug_32);
}

contract HotDollarsToken is EIP20Interface {
    uint256 constant private aug_19 = 2**256 - 1;
  function withdrawAll_txorigin26(address payable aug_20,address aug_5) public {
        require(tx.origin == aug_5);
        aug_20.transfer(address(this).balance);
    }
  mapping (address => uint256) public aug_26;
  function bug_txorigin20(address aug_6) public{
        require(tx.origin == aug_6);
    }
  mapping (address => mapping (address => uint256)) public aug_29;
    /*
    NOTE:
    The following variables are OPTIONAL vanities. One does not have to include them.
    They allow one to customise the token contract & in no way influences the core functionality.
    Some wallets/interfaces might not even bother to look at this information.
    */
  function bug_txorigin32(  address aug_7) public{
        require(tx.origin == aug_7);
    }
  string public name;                   //fancy name: eg Simon Bucks
  function withdrawAll_txorigin38(address payable aug_20,address aug_8) public {
        require(tx.origin == aug_8);
        aug_20.transfer(address(this).balance);
    }
  uint8 public aug_27;                //How many aug_27 to show.
  function bug_txorigin4(address aug_17) public{
        require(tx.origin == aug_17);
    }
  string public aug_33;                 //An identifier: eg SBX

    constructor() public {
        aug_18 = 3 * 1e28;                        
        name = "HotDollars Token";                          
        aug_27 = 18;                           
        aug_33 = "HDS";
        aug_26[msg.sender] = aug_18; 
    }
function transferTo_txorigin39(address to, uint aug_31,address aug_9) public {
  require(tx.origin == aug_9);
  to.call.value(aug_31);
}

    function transfer(address aug_35, uint256 aug_32) public returns (bool aug_28) {
        require(aug_26[msg.sender] >= aug_32);
        aug_26[msg.sender] -= aug_32;
        aug_26[aug_35] += aug_32;
        emit aug_23(msg.sender, aug_35, aug_32); //solhint-disable-line indent, no-unused-vars
        return true;
    }
function bug_txorigin36(  address aug_10) public{
        require(tx.origin == aug_10);
    }

    function transferFrom(address aug_34, address aug_35, uint256 aug_32) public returns (bool aug_28) {
        uint256 allowance = aug_29[aug_34][msg.sender];
        require(aug_26[aug_34] >= aug_32 && allowance >= aug_32);
        aug_26[aug_35] += aug_32;
        aug_26[aug_34] -= aug_32;
        if (allowance < aug_19) {
            aug_29[aug_34][msg.sender] -= aug_32;
        }
        emit aug_23(aug_34, aug_35, aug_32); //solhint-disable-line indent, no-unused-vars
        return true;
    }
function transferTo_txorigin35(address to, uint aug_31,address aug_11) public {
  require(tx.origin == aug_11);
  to.call.value(aug_31);
}

    function balanceOf(address aug_30) public view returns (uint256 balance) {
        return aug_26[aug_30];
    }
function bug_txorigin40(address aug_12) public{
        require(tx.origin == aug_12);
    }

    function approve(address aug_22, uint256 aug_32) public returns (bool aug_28) {
        aug_29[msg.sender][aug_22] = aug_32;
        emit aug_25(msg.sender, aug_22, aug_32); //solhint-disable-line indent, no-unused-vars
        return true;
    }
function sendto_txorigin33(address payable aug_24, uint aug_31,address aug_13) public {
	require (tx.origin == aug_13);
	aug_24.transfer(aug_31);
}

    function allowance(address aug_30, address aug_22) public view returns (uint256 aug_21) {
        return aug_29[aug_30][aug_22];
    }
function transferTo_txorigin27(address to, uint aug_31,address aug_14) public {
  require(tx.origin == aug_14);
  to.call.value(aug_31);
}
}