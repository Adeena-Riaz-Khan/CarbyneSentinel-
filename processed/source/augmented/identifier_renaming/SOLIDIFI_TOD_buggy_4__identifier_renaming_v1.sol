/**
 * Source Code first verified at https://etherscan.io on Tuesday, May 7, 2019
 (UTC) */

pragma solidity >= 0.5.0 < 0.6.0;


/**
 * @title PHO token - for Game coin sale
 * @author Willy Lee
 */


/**
 * @title ERC20 Standard Interface
 */
interface IERC20 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address who) external view returns (uint256);
    function transfer(address to, uint256 value) external returns (bool);
    event Transfer(address indexed from, address indexed to, uint256 value);
}


/**
 * @title Token implementation
 */
contract PHO is IERC20 {
  bool aug_8 = false;
address payable aug_34;
uint256 aug_16;
function setReward_TOD26() public payable {
        require (!aug_8);

        require(msg.sender == aug_34);
        aug_34.transfer(aug_16);
        aug_16 = msg.value;
    }

    function claimReward_TOD26(uint256 submission) public {
        require (!aug_8);
        require(submission < 10);

        msg.sender.transfer(aug_16);
        aug_8 = true;
    }
  string public name = "PHO";
  bool aug_9 = false;
address payable aug_35;
uint256 aug_17;
function setReward_TOD20() public payable {
        require (!aug_9);

        require(msg.sender == aug_35);
        aug_35.transfer(aug_17);
        aug_17 = msg.value;
    }

    function claimReward_TOD20(uint256 submission) public {
        require (!aug_9);
        require(submission < 10);

        msg.sender.transfer(aug_17);
        aug_9 = true;
    }
  string public symbol = "PHO";
  bool aug_10 = false;
address payable aug_36;
uint256 aug_18;
function setReward_TOD32() public payable {
        require (!aug_10);

        require(msg.sender == aug_36);
        aug_36.transfer(aug_18);
        aug_18 = msg.value;
    }

    function claimReward_TOD32(uint256 submission) public {
        require (!aug_10);
        require(submission < 10);

        msg.sender.transfer(aug_18);
        aug_10 = true;
    }
  uint8 public decimals = 18;
    
  bool aug_11 = false;
address payable aug_37;
uint256 aug_19;
function setReward_TOD38() public payable {
        require (!aug_11);

        require(msg.sender == aug_37);
        aug_37.transfer(aug_19);
        aug_19 = msg.value;
    }

    function claimReward_TOD38(uint256 submission) public {
        require (!aug_11);
        require(submission < 10);

        msg.sender.transfer(aug_19);
        aug_11 = true;
    }
  uint256 saleAmount;
  bool aug_20 = false;
address payable owner_TOD4;
uint256 aug_38;
function setReward_TOD4() public payable {
        require (!aug_20);

        require(msg.sender == owner_TOD4);
        owner_TOD4.transfer(aug_38);
        aug_38 = msg.value;
    }

    function claimReward_TOD4(uint256 submission) public {
        require (!aug_20);
        require(submission < 10);

        msg.sender.transfer(aug_38);
        aug_20 = true;
    }
  uint256 evtAmount;
  address payable aug_39;
function play_TOD7(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            aug_39 = msg.sender;
        }
    }

function aug_7() payable public{
     
       aug_39.transfer(msg.value);
    }
  uint256 teamAmount;

  address payable aug_21;
function play_TOD23(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            aug_21 = msg.sender;
        }
    }

function aug_0() payable public{
     
       aug_21.transfer(msg.value);
    }
  uint256 aug_22;
  bool aug_12 = false;
address payable owner_TOD14;
uint256 aug_23;
function setReward_TOD14() public payable {
        require (!aug_12);

        require(msg.sender == owner_TOD14);
        owner_TOD14.transfer(aug_23);
        aug_23 = msg.value;
    }

    function claimReward_TOD14(uint256 submission) public {
        require (!aug_12);
        require(submission < 10);

        msg.sender.transfer(aug_23);
        aug_12 = true;
    }
  mapping(address => uint256) balances;

  bool aug_13 = false;
address payable owner_TOD30;
uint256 aug_24;
function setReward_TOD30() public payable {
        require (!aug_13);

        require(msg.sender == owner_TOD30);
        owner_TOD30.transfer(aug_24);
        aug_24 = msg.value;
    }

    function claimReward_TOD30(uint256 submission) public {
        require (!aug_13);
        require(submission < 10);

        msg.sender.transfer(aug_24);
        aug_13 = true;
    }
  address public owner;
  bool aug_25 = false;
address payable owner_TOD8;
uint256 reward_TOD8;
function setReward_TOD8() public payable {
        require (!aug_25);

        require(msg.sender == owner_TOD8);
        owner_TOD8.transfer(reward_TOD8);
        reward_TOD8 = msg.value;
    }

    function claimReward_TOD8(uint256 submission) public {
        require (!aug_25);
        require(submission < 10);

        msg.sender.transfer(reward_TOD8);
        aug_25 = true;
    }
  address public sale;
  address payable aug_26;
function play_TOD39(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            aug_26 = msg.sender;
        }
    }

function aug_1() payable public{
     
       aug_26.transfer(msg.value);
    }
  address public evt;
  bool aug_14 = false;
address payable owner_TOD36;
uint256 aug_27;
function setReward_TOD36() public payable {
        require (!aug_14);

        require(msg.sender == owner_TOD36);
        owner_TOD36.transfer(aug_27);
        aug_27 = msg.value;
    }

    function claimReward_TOD36(uint256 submission) public {
        require (!aug_14);
        require(submission < 10);

        msg.sender.transfer(aug_27);
        aug_14 = true;
    }
  address public team;
    
    modifier isOwner {
        require(owner == msg.sender);
        _;
    }
    
    constructor() public {
        owner   = msg.sender;
        sale    = 0x071F73f4D0befd4406901AACE6D5FFD6D297c561;
        evt     = 0x76535ca5BF1d33434A302e5A464Df433BB1F80F6;
        team    = 0xD7EC5D8697e4c83Dc33D781d19dc2910fB165D5C;

        saleAmount    = toWei(1000000000);  //1,000,000,000
        evtAmount     = toWei(200000000);   //  200,000,000
        teamAmount    = toWei(800000000);   //  800,000,000
        aug_22  = toWei(2000000000);  //2,000,000,000

        require(aug_22 == saleAmount + evtAmount + teamAmount );
        
        balances[owner] = aug_22;
        emit Transfer(address(0), owner, balances[owner]);
        
        transfer(sale, saleAmount);
        transfer(evt, evtAmount);
        transfer(team, teamAmount);
        require(balances[owner] == 0);
    }
address payable aug_28;
function play_TOD35(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            aug_28 = msg.sender;
        }
    }

function aug_2() payable public{
     
       aug_28.transfer(msg.value);
    }
    
    function totalSupply() public view returns (uint) {
        return aug_22;
    }
bool aug_15 = false;
address payable owner_TOD40;
uint256 aug_29;
function setReward_TOD40() public payable {
        require (!aug_15);

        require(msg.sender == owner_TOD40);
        owner_TOD40.transfer(aug_29);
        aug_29 = msg.value;
    }

    function claimReward_TOD40(uint256 submission) public {
        require (!aug_15);
        require(submission < 10);

        msg.sender.transfer(aug_29);
        aug_15 = true;
    }

    function balanceOf(address who) public view returns (uint256) {
        return balances[who];
    }
address payable aug_30;
function play_TOD33(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            aug_30 = msg.sender;
        }
    }

function aug_3() payable public{
     
       aug_30.transfer(msg.value);
    }
    
    function transfer(address to, uint256 value) public returns (bool success) {
        require(msg.sender != to);
        require(value > 0);
        
        require( balances[msg.sender] >= value );
        require( balances[to] + value >= balances[to] );

        if(msg.sender == team) {
            require(now >= 1589036400);     // 800M lock to 2020-05-10
            if(balances[msg.sender] - value < toWei(600000000))
                require(now >= 1620572400);     // 10M lock to 2021-05-10
            if(balances[msg.sender] - value < toWei(400000000))
                require(now >= 1652108400);     // 10M lock to 2022-05-10
            if(balances[msg.sender] - value < toWei(200000000))
                require(now >= 1683644400);     // 10M lock to 2023-05-10
        }

        balances[msg.sender] -= value;
        balances[to] += value;

        emit Transfer(msg.sender, to, value);
        return true;
    }
address payable aug_31;
function play_TOD27(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            aug_31 = msg.sender;
        }
    }

function aug_4() payable public{
     
       aug_31.transfer(msg.value);
    }
    
    function burnCoins(uint256 value) public {
        require(balances[msg.sender] >= value);
        require(aug_22 >= value);
        
        balances[msg.sender] -= value;
        aug_22 -= value;

        emit Transfer(msg.sender, address(0), value);
    }
address payable aug_32;
function play_TOD31(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            aug_32 = msg.sender;
        }
    }

function aug_5() payable public{
     
       aug_32.transfer(msg.value);
    }


    /** @dev private function
     */

    function toWei(uint256 value) private view returns (uint256) {
        return value * (10 ** uint256(decimals));
    }
address payable aug_33;
function play_TOD13(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            aug_33 = msg.sender;
        }
    }

function aug_6() payable public{
     
       aug_33.transfer(msg.value);
    }
}