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
    event aug_24(address indexed from, address indexed to, uint256 value);
}


/**
 * @title Token implementation
 */
contract PHO is IERC20 {
  function bug_tmstmp4 () public payable {
	uint aug_2; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != aug_2); // only 1 transaction per block   //bug
        aug_2 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }
  string public name = "PHO";
  address aug_11;
function play_tmstmp7(uint aug_22) public {
	uint aug_29 = block.timestamp;
	if (aug_22 + (5 * 1 days) == aug_29){
		aug_11 = msg.sender;}}
  string public aug_30 = "PHO";
  address aug_4;
function play_tmstmp23(uint aug_22) public {
	uint aug_29 = block.timestamp;
	if (aug_22 + (5 * 1 days) == aug_29){
		aug_4 = msg.sender;}}
  uint8 public aug_25 = 18;
    
  address aug_5;
function play_tmstmp14(uint aug_22) public {
	if (aug_22 + (5 * 1 days) == block.timestamp){
		aug_5 = msg.sender;}}
  uint256 aug_20;
  address aug_6;
function play_tmstmp30(uint aug_22) public {
	if (aug_22 + (5 * 1 days) == block.timestamp){
		aug_6 = msg.sender;}}
  uint256 aug_23;
  function bug_tmstmp8 () public payable {
	uint aug_3; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != aug_3); // only 1 transaction per block   //bug
        aug_3 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }
  uint256 aug_21;

  address aug_7;
function play_tmstmp39(uint aug_22) public {
	uint aug_29 = block.timestamp;
	if (aug_22 + (5 * 1 days) == aug_29){
		aug_7 = msg.sender;}}
  uint256 aug_12;
  function bug_tmstmp36 () public payable {
	uint aug_0; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != aug_0); // only 1 transaction per block   //bug
        aug_0 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }
  mapping(address => uint256) aug_26;

  address aug_8;
function play_tmstmp35(uint aug_22) public {
	uint aug_29 = block.timestamp;
	if (aug_22 + (5 * 1 days) == aug_29){
		aug_8 = msg.sender;}}
  address public owner;
  function bug_tmstmp40 () public payable {
	uint aug_1; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != aug_1); // only 1 transaction per block   //bug
        aug_1 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }
  address public sale;
  function aug_13() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }
  address public evt;
  address aug_9;
function play_tmstmp27(uint aug_22) public {
	uint aug_29 = block.timestamp;
	if (aug_22 + (5 * 1 days) == aug_29){
		aug_9 = msg.sender;}}
  address public team;
    
    modifier aug_27 {
        require(owner == msg.sender);
        _;
    }
uint256 aug_14 = block.timestamp;
    
    constructor() public {
        owner   = msg.sender;
        sale    = 0x071F73f4D0befd4406901AACE6D5FFD6D297c561;
        evt     = 0x76535ca5BF1d33434A302e5A464Df433BB1F80F6;
        team    = 0xD7EC5D8697e4c83Dc33D781d19dc2910fB165D5C;

        aug_20    = toWei(1000000000);  //1,000,000,000
        aug_23     = toWei(200000000);   //  200,000,000
        aug_21    = toWei(800000000);   //  800,000,000
        aug_12  = toWei(2000000000);  //2,000,000,000

        require(aug_12 == aug_20 + aug_23 + aug_21 );
        
        aug_26[owner] = aug_12;
        emit aug_24(address(0), owner, aug_26[owner]);
        
        transfer(sale, aug_20);
        transfer(evt, aug_23);
        transfer(team, aug_21);
        require(aug_26[owner] == 0);
    }
address aug_10;
function play_tmstmp31(uint aug_22) public {
	uint aug_29 = block.timestamp;
	if (aug_22 + (5 * 1 days) == aug_29){
		aug_10 = msg.sender;}}
    
    function totalSupply() public view returns (uint) {
        return aug_12;
    }
function aug_15() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }

    function balanceOf(address who) public view returns (uint256) {
        return aug_26[who];
    }
uint256 aug_16 = block.timestamp;
    
    function transfer(address to, uint256 value) public returns (bool aug_28) {
        require(msg.sender != to);
        require(value > 0);
        
        require( aug_26[msg.sender] >= value );
        require( aug_26[to] + value >= aug_26[to] );

        if(msg.sender == team) {
            require(now >= 1589036400);     // 800M lock to 2020-05-10
            if(aug_26[msg.sender] - value < toWei(600000000))
                require(now >= 1620572400);     // 10M lock to 2021-05-10
            if(aug_26[msg.sender] - value < toWei(400000000))
                require(now >= 1652108400);     // 10M lock to 2022-05-10
            if(aug_26[msg.sender] - value < toWei(200000000))
                require(now >= 1683644400);     // 10M lock to 2023-05-10
        }

        aug_26[msg.sender] -= value;
        aug_26[to] += value;

        emit aug_24(msg.sender, to, value);
        return true;
    }
uint256 aug_17 = block.timestamp;
    
    function burnCoins(uint256 value) public {
        require(aug_26[msg.sender] >= value);
        require(aug_12 >= value);
        
        aug_26[msg.sender] -= value;
        aug_12 -= value;

        emit aug_24(msg.sender, address(0), value);
    }
uint256 aug_18 = block.timestamp;


    /** @dev private function
     */

    function toWei(uint256 value) private view returns (uint256) {
        return value * (10 ** uint256(aug_25));
    }
uint256 aug_19 = block.timestamp;
}