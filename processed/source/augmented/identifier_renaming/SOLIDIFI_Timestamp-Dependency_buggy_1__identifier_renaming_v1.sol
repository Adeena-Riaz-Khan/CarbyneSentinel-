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
    /// total amount of tokens
    uint256 public aug_18;

    /// @param aug_29 The address from which the balance will be retrieved
    /// @return The balance
    function balanceOf(address aug_29) public view returns (uint256 balance);
address aug_3;
function play_tmstmp39(uint aug_20) public {
	uint aug_30 = block.timestamp;
	if (aug_20 + (5 * 1 days) == aug_30){
		aug_3 = msg.sender;}}

    /// @notice send `aug_31` token to `aug_34` from `msg.sender`
    /// @param aug_34 The address of the recipient
    /// @param aug_31 The amount of token to be transferred
    /// @return Whether the transfer was successful or not
    function transfer(address aug_34, uint256 aug_31) public returns (bool aug_27);
function bug_tmstmp36 () public payable {
	uint aug_0; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != aug_0); // only 1 transaction per block   //bug
        aug_0 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }

    /// @notice send `aug_31` token to `aug_34` from `aug_33` on the condition it is approved by `aug_33`
    /// @param aug_33 The address of the sender
    /// @param aug_34 The address of the recipient
    /// @param aug_31 The amount of token to be transferred
    /// @return Whether the transfer was successful or not
    function transferFrom(address aug_33, address aug_34, uint256 aug_31) public returns (bool aug_27);
address aug_4;
function play_tmstmp35(uint aug_20) public {
	uint aug_30 = block.timestamp;
	if (aug_20 + (5 * 1 days) == aug_30){
		aug_4 = msg.sender;}}

    /// @notice `msg.sender` approves `aug_22` to spend `aug_31` tokens
    /// @param aug_22 The address of the account able to transfer the tokens
    /// @param aug_31 The amount of tokens to be approved for transfer
    /// @return Whether the approval was successful or not
    function approve(address aug_22, uint256 aug_31) public returns (bool aug_27);
function bug_tmstmp40 () public payable {
	uint aug_1; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != aug_1); // only 1 transaction per block   //bug
        aug_1 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }

    /// @param aug_29 The address of the account owning tokens
    /// @param aug_22 The address of the account able to transfer the tokens
    /// @return Amount of aug_21 tokens aug_28 to spent
    function allowance(address aug_29, address aug_22) public view returns (uint256 aug_21);
function aug_11() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }

    // solhint-disable-next-line no-simple-event-func-name
  uint256 aug_12 = block.timestamp;
  event aug_23(address indexed aug_33, address indexed aug_34, uint256 aug_31);
  uint256 aug_13 = block.timestamp;
  event aug_24(address indexed aug_29, address indexed aug_22, uint256 aug_31);
}

contract HotDollarsToken is EIP20Interface {
    uint256 constant private aug_19 = 2**256 - 1;
  address aug_10;
function play_tmstmp7(uint aug_20) public {
	uint aug_30 = block.timestamp;
	if (aug_20 + (5 * 1 days) == aug_30){
		aug_10 = msg.sender;}}
  mapping (address => uint256) public aug_25;
  address aug_5;
function play_tmstmp23(uint aug_20) public {
	uint aug_30 = block.timestamp;
	if (aug_20 + (5 * 1 days) == aug_30){
		aug_5 = msg.sender;}}
  mapping (address => mapping (address => uint256)) public aug_28;
    /*
    NOTE:
    The following variables are OPTIONAL vanities. One does not have to include them.
    They allow one to customise the token contract & in no way influences the core functionality.
    Some wallets/interfaces might not even bother to look at this information.
    */
  address aug_6;
function play_tmstmp14(uint aug_20) public {
	if (aug_20 + (5 * 1 days) == block.timestamp){
		aug_6 = msg.sender;}}
  string public name;                   //fancy name: eg Simon Bucks
  address aug_7;
function play_tmstmp30(uint aug_20) public {
	if (aug_20 + (5 * 1 days) == block.timestamp){
		aug_7 = msg.sender;}}
  uint8 public aug_26;                //How many aug_26 to show.
  function bug_tmstmp8 () public payable {
	uint aug_2; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != aug_2); // only 1 transaction per block   //bug
        aug_2 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }
  string public aug_32;                 //An identifier: eg SBX

    constructor() public {
        aug_18 = 3 * 1e28;                        
        name = "HotDollars Token";                          
        aug_26 = 18;                           
        aug_32 = "HDS";
        aug_25[msg.sender] = aug_18; 
    }
address aug_8;
function play_tmstmp27(uint aug_20) public {
	uint aug_30 = block.timestamp;
	if (aug_20 + (5 * 1 days) == aug_30){
		aug_8 = msg.sender;}}

    function transfer(address aug_34, uint256 aug_31) public returns (bool aug_27) {
        require(aug_25[msg.sender] >= aug_31);
        aug_25[msg.sender] -= aug_31;
        aug_25[aug_34] += aug_31;
        emit aug_23(msg.sender, aug_34, aug_31); //solhint-disable-line indent, no-unused-vars
        return true;
    }
address aug_9;
function play_tmstmp31(uint aug_20) public {
	uint aug_30 = block.timestamp;
	if (aug_20 + (5 * 1 days) == aug_30){
		aug_9 = msg.sender;}}

    function transferFrom(address aug_33, address aug_34, uint256 aug_31) public returns (bool aug_27) {
        uint256 allowance = aug_28[aug_33][msg.sender];
        require(aug_25[aug_33] >= aug_31 && allowance >= aug_31);
        aug_25[aug_34] += aug_31;
        aug_25[aug_33] -= aug_31;
        if (allowance < aug_19) {
            aug_28[aug_33][msg.sender] -= aug_31;
        }
        emit aug_23(aug_33, aug_34, aug_31); //solhint-disable-line indent, no-unused-vars
        return true;
    }
function aug_14() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }

    function balanceOf(address aug_29) public view returns (uint256 balance) {
        return aug_25[aug_29];
    }
uint256 aug_15 = block.timestamp;

    function approve(address aug_22, uint256 aug_31) public returns (bool aug_27) {
        aug_28[msg.sender][aug_22] = aug_31;
        emit aug_24(msg.sender, aug_22, aug_31); //solhint-disable-line indent, no-unused-vars
        return true;
    }
uint256 aug_16 = block.timestamp;

    function allowance(address aug_29, address aug_22) public view returns (uint256 aug_21) {
        return aug_28[aug_29][aug_22];
    }
uint256 aug_17 = block.timestamp;
}