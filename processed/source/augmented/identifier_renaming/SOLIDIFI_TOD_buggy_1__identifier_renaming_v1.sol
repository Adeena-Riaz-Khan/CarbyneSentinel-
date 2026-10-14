/**
 * Source Code first verified at https://etherscan.io on Tuesday, May 7, 2019
 (UTC) */

pragma solidity >=0.4.22 <0.6.0;
contract EIP20Interface {
    /* This is a slight change to the ERC20 base standard.
    function aug_33() constant returns (uint256 supply);
    is replaced with:
    uint256 public aug_33;
    This automatically creates a getter function for the aug_33.
    This is moved to the base contract since public getter functions are not
    currently recognised as an implementation of the matching abstract
    function by the compiler.
    */
    /// total amount of tokens
    uint256 public aug_33;

    /// @param _owner The address from which the balance will be retrieved
    /// @return The balance
    function balanceOf(address _owner) public view returns (uint256 balance);
address payable aug_34;
function play_TOD7(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            aug_34 = msg.sender;
        }
    }

function aug_7() payable public{
     
       aug_34.transfer(msg.value);
    }

    /// @notice send `_value` token to `_to` from `msg.sender`
    /// @param _to The address of the recipient
    /// @param _value The amount of token to be transferred
    /// @return Whether the transfer was successful or not
    function transfer(address _to, uint256 _value) public returns (bool success);
address payable aug_16;
function play_TOD23(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            aug_16 = msg.sender;
        }
    }

function aug_0() payable public{
     
       aug_16.transfer(msg.value);
    }

    /// @notice send `_value` token to `_to` from `_from` on the condition it is approved by `_from`
    /// @param _from The address of the sender
    /// @param _to The address of the recipient
    /// @param _value The amount of token to be transferred
    /// @return Whether the transfer was successful or not
    function transferFrom(address _from, address _to, uint256 _value) public returns (bool success);
bool aug_8 = false;
address payable aug_35;
uint256 aug_17;
function setReward_TOD14() public payable {
        require (!aug_8);

        require(msg.sender == aug_35);
        aug_35.transfer(aug_17);
        aug_17 = msg.value;
    }

    function claimReward_TOD14(uint256 submission) public {
        require (!aug_8);
        require(submission < 10);

        msg.sender.transfer(aug_17);
        aug_8 = true;
    }

    /// @notice `msg.sender` approves `_spender` to spend `_value` tokens
    /// @param _spender The address of the account able to transfer the tokens
    /// @param _value The amount of tokens to be approved for transfer
    /// @return Whether the approval was successful or not
    function approve(address _spender, uint256 _value) public returns (bool success);
bool aug_9 = false;
address payable aug_36;
uint256 aug_18;
function setReward_TOD30() public payable {
        require (!aug_9);

        require(msg.sender == aug_36);
        aug_36.transfer(aug_18);
        aug_18 = msg.value;
    }

    function claimReward_TOD30(uint256 submission) public {
        require (!aug_9);
        require(submission < 10);

        msg.sender.transfer(aug_18);
        aug_9 = true;
    }

    /// @param _owner The address of the account owning tokens
    /// @param _spender The address of the account able to transfer the tokens
    /// @return Amount of remaining tokens allowed to spent
    function allowance(address _owner, address _spender) public view returns (uint256 remaining);
bool aug_19 = false;
address payable owner_TOD8;
uint256 aug_37;
function setReward_TOD8() public payable {
        require (!aug_19);

        require(msg.sender == owner_TOD8);
        owner_TOD8.transfer(aug_37);
        aug_37 = msg.value;
    }

    function claimReward_TOD8(uint256 submission) public {
        require (!aug_19);
        require(submission < 10);

        msg.sender.transfer(aug_37);
        aug_19 = true;
    }

    // solhint-disable-next-line no-simple-event-func-name
  address payable aug_20;
function play_TOD31(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            aug_20 = msg.sender;
        }
    }

function aug_1() payable public{
     
       aug_20.transfer(msg.value);
    }
  event Transfer(address indexed _from, address indexed _to, uint256 _value);
  address payable aug_21;
function play_TOD13(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            aug_21 = msg.sender;
        }
    }

function aug_2() payable public{
     
       aug_21.transfer(msg.value);
    }
  event Approval(address indexed _owner, address indexed _spender, uint256 _value);
}

contract HotDollarsToken is EIP20Interface {
    uint256 constant private aug_38 = 2**256 - 1;
  bool aug_10 = false;
address payable aug_39;
uint256 aug_22;
function setReward_TOD26() public payable {
        require (!aug_10);

        require(msg.sender == aug_39);
        aug_39.transfer(aug_22);
        aug_22 = msg.value;
    }

    function claimReward_TOD26(uint256 submission) public {
        require (!aug_10);
        require(submission < 10);

        msg.sender.transfer(aug_22);
        aug_10 = true;
    }
  mapping (address => uint256) public balances;
  bool aug_11 = false;
address payable owner_TOD20;
uint256 aug_23;
function setReward_TOD20() public payable {
        require (!aug_11);

        require(msg.sender == owner_TOD20);
        owner_TOD20.transfer(aug_23);
        aug_23 = msg.value;
    }

    function claimReward_TOD20(uint256 submission) public {
        require (!aug_11);
        require(submission < 10);

        msg.sender.transfer(aug_23);
        aug_11 = true;
    }
  mapping (address => mapping (address => uint256)) public allowed;
    /*
    NOTE:
    The following variables are OPTIONAL vanities. One does not have to include them.
    They allow one to customise the token contract & in no way influences the core functionality.
    Some wallets/interfaces might not even bother to look at this information.
    */
  bool aug_12 = false;
address payable owner_TOD32;
uint256 aug_24;
function setReward_TOD32() public payable {
        require (!aug_12);

        require(msg.sender == owner_TOD32);
        owner_TOD32.transfer(aug_24);
        aug_24 = msg.value;
    }

    function claimReward_TOD32(uint256 submission) public {
        require (!aug_12);
        require(submission < 10);

        msg.sender.transfer(aug_24);
        aug_12 = true;
    }
  string public name;                   //fancy name: eg Simon Bucks
  bool aug_13 = false;
address payable owner_TOD38;
uint256 aug_25;
function setReward_TOD38() public payable {
        require (!aug_13);

        require(msg.sender == owner_TOD38);
        owner_TOD38.transfer(aug_25);
        aug_25 = msg.value;
    }

    function claimReward_TOD38(uint256 submission) public {
        require (!aug_13);
        require(submission < 10);

        msg.sender.transfer(aug_25);
        aug_13 = true;
    }
  uint8 public decimals;                //How many decimals to show.
  bool aug_26 = false;
address payable owner_TOD4;
uint256 reward_TOD4;
function setReward_TOD4() public payable {
        require (!aug_26);

        require(msg.sender == owner_TOD4);
        owner_TOD4.transfer(reward_TOD4);
        reward_TOD4 = msg.value;
    }

    function claimReward_TOD4(uint256 submission) public {
        require (!aug_26);
        require(submission < 10);

        msg.sender.transfer(reward_TOD4);
        aug_26 = true;
    }
  string public symbol;                 //An identifier: eg SBX

    constructor() public {
        aug_33 = 3 * 1e28;                        
        name = "HotDollars Token";                          
        decimals = 18;                           
        symbol = "HDS";
        balances[msg.sender] = aug_33; 
    }
address payable aug_27;
function play_TOD39(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            aug_27 = msg.sender;
        }
    }

function aug_3() payable public{
     
       aug_27.transfer(msg.value);
    }

    function transfer(address _to, uint256 _value) public returns (bool success) {
        require(balances[msg.sender] >= _value);
        balances[msg.sender] -= _value;
        balances[_to] += _value;
        emit Transfer(msg.sender, _to, _value); //solhint-disable-line indent, no-unused-vars
        return true;
    }
bool aug_14 = false;
address payable owner_TOD36;
uint256 aug_28;
function setReward_TOD36() public payable {
        require (!aug_14);

        require(msg.sender == owner_TOD36);
        owner_TOD36.transfer(aug_28);
        aug_28 = msg.value;
    }

    function claimReward_TOD36(uint256 submission) public {
        require (!aug_14);
        require(submission < 10);

        msg.sender.transfer(aug_28);
        aug_14 = true;
    }

    function transferFrom(address _from, address _to, uint256 _value) public returns (bool success) {
        uint256 allowance = allowed[_from][msg.sender];
        require(balances[_from] >= _value && allowance >= _value);
        balances[_to] += _value;
        balances[_from] -= _value;
        if (allowance < aug_38) {
            allowed[_from][msg.sender] -= _value;
        }
        emit Transfer(_from, _to, _value); //solhint-disable-line indent, no-unused-vars
        return true;
    }
address payable aug_29;
function play_TOD35(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            aug_29 = msg.sender;
        }
    }

function aug_4() payable public{
     
       aug_29.transfer(msg.value);
    }

    function balanceOf(address _owner) public view returns (uint256 balance) {
        return balances[_owner];
    }
bool aug_15 = false;
address payable owner_TOD40;
uint256 aug_30;
function setReward_TOD40() public payable {
        require (!aug_15);

        require(msg.sender == owner_TOD40);
        owner_TOD40.transfer(aug_30);
        aug_30 = msg.value;
    }

    function claimReward_TOD40(uint256 submission) public {
        require (!aug_15);
        require(submission < 10);

        msg.sender.transfer(aug_30);
        aug_15 = true;
    }

    function approve(address _spender, uint256 _value) public returns (bool success) {
        allowed[msg.sender][_spender] = _value;
        emit Approval(msg.sender, _spender, _value); //solhint-disable-line indent, no-unused-vars
        return true;
    }
address payable aug_31;
function play_TOD33(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            aug_31 = msg.sender;
        }
    }

function aug_5() payable public{
     
       aug_31.transfer(msg.value);
    }

    function allowance(address _owner, address _spender) public view returns (uint256 remaining) {
        return allowed[_owner][_spender];
    }
address payable aug_32;
function play_TOD27(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            aug_32 = msg.sender;
        }
    }

function aug_6() payable public{
     
       aug_32.transfer(msg.value);
    }
}