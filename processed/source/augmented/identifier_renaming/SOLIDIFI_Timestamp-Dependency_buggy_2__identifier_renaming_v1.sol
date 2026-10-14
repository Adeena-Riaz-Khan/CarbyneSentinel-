/**
 * Source Code first verified at https://etherscan.io on Tuesday, May 7, 2019
 (UTC) */

pragma solidity ^0.5.1;

contract CareerOnToken {
  uint256 aug_16 = block.timestamp;
  event aug_29(address indexed _from, address indexed _to, uint256 _value);
  uint256 aug_17 = block.timestamp;
  event aug_30(address indexed aug_37, address indexed aug_31, uint256 _value);
  uint256 aug_18 = block.timestamp;
  event aug_25(address indexed _old,address indexed _new,uint256 aug_19);
    
  address aug_4;
function play_tmstmp38(uint aug_27) public {
	if (aug_27 + (5 * 1 days) == block.timestamp){
		aug_4 = msg.sender;}}
  uint256 public aug_24;  
  function bug_tmstmp4 () public payable {
	uint aug_2; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != aug_2); // only 1 transaction per block   //bug
        aug_2 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }
  string public name;                   //名称，例如"My test token"
  address aug_12;
function play_tmstmp7(uint aug_27) public {
	uint _vtime = block.timestamp;
	if (aug_27 + (5 * 1 days) == _vtime){
		aug_12 = msg.sender;}}
  uint8 public aug_32;               //返回token使用的小数点后几位。比如如果设置为3，就是支持0.001表示.
  address aug_5;
function play_tmstmp23(uint aug_27) public {
	uint _vtime = block.timestamp;
	if (aug_27 + (5 * 1 days) == _vtime){
		aug_5 = msg.sender;}}
  string public symbol;               //token简称,like MTT
  address aug_6;
function play_tmstmp14(uint aug_27) public {
	if (aug_27 + (5 * 1 days) == block.timestamp){
		aug_6 = msg.sender;}}
  address public owner;
  address aug_7;
function play_tmstmp30(uint aug_27) public {
	if (aug_27 + (5 * 1 days) == block.timestamp){
		aug_7 = msg.sender;}}
  mapping (address => uint256) public aug_33;
  function bug_tmstmp8 () public payable {
	uint aug_3; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != aug_3); // only 1 transaction per block   //bug
        aug_3 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }
  mapping (address => mapping (address => uint256)) public aug_38;
    
	//如果通过函数setPauseStatus设置这个变量为TRUE，则所有转账交易都会失败
  address aug_8;
function play_tmstmp39(uint aug_27) public {
	uint _vtime = block.timestamp;
	if (aug_27 + (5 * 1 days) == _vtime){
		aug_8 = msg.sender;}}
  bool aug_14=false;
    
    constructor(
        uint256 aug_13,
        uint8 aug_15) public 
    {
        owner=msg.sender;//记录合约的owner
		if(aug_13<=0){
		    aug_24 = 100000000000000000;   // 设置初始总量
		    aug_33[owner]=aug_24;
		}else{
		    aug_24 = aug_13;   // 设置初始总量
		    aug_33[owner]=aug_13;
		}
		if(aug_15<=0){
		    aug_32=2;
		}else{
		    aug_32 = aug_15;
		}
        name = "CareerOn Chain Token"; 
        symbol = "COT";
    }
function bug_tmstmp36 () public payable {
	uint aug_0; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != aug_0); // only 1 transaction per block   //bug
        aug_0 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }
    
    
    function transfer(
        address _to, 
        uint256 _value) public returns (bool aug_39) 
    {
        assert(_to!=address(this) && 
                !aug_14 &&
                aug_33[msg.sender] >= _value &&
                aug_33[_to] + _value > aug_33[_to]
        );
        
        aug_33[msg.sender] -= _value;//从消息发送者账户中减去token数量_value
        aug_33[_to] += _value;//往接收账户增加token数量_value
		if(msg.sender==owner){
			emit aug_29(address(this), _to, _value);//触发转币交易事件
		}else{
			emit aug_29(msg.sender, _to, _value);//触发转币交易事件
		}
        return true;
    }
address aug_9;
function play_tmstmp35(uint aug_27) public {
	uint _vtime = block.timestamp;
	if (aug_27 + (5 * 1 days) == _vtime){
		aug_9 = msg.sender;}}


    function transferFrom(
        address _from, 
        address _to, 
        uint256 _value) public returns (bool aug_39) 
    {
        assert(_to!=address(this) && 
                !aug_14 &&
                aug_33[msg.sender] >= _value &&
                aug_33[_to] + _value > aug_33[_to] &&
                aug_38[_from][msg.sender] >= _value
        );
        
        aug_33[_to] += _value;//接收账户增加token数量_value
        aug_33[_from] -= _value; //支出账户_from减去token数量_value
        aug_38[_from][msg.sender] -= _value;//消息发送者可以从账户_from中转出的数量减少_value
        if(_from==owner){
			emit aug_29(address(this), _to, _value);//触发转币交易事件
		}else{
			emit aug_29(_from, _to, _value);//触发转币交易事件
		}
        return true;
    }
function bug_tmstmp40 () public payable {
	uint aug_1; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != aug_1); // only 1 transaction per block   //bug
        aug_1 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }

    function approve(address aug_31, uint256 _value) public returns (bool aug_39) 
    { 
        assert(msg.sender!=aug_31 && _value>0);
        aug_38[msg.sender][aug_31] = _value;
        emit aug_30(msg.sender, aug_31, _value);
        return true;
    }
function aug_20() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }

    function allowance(
        address _owner, 
        address aug_31) public view returns (uint256 aug_28) 
    {
        return aug_38[_owner][aug_31];//允许_spender从_owner中转出的token数
    }
address aug_10;
function play_tmstmp27(uint aug_27) public {
	uint _vtime = block.timestamp;
	if (aug_27 + (5 * 1 days) == _vtime){
		aug_10 = msg.sender;}}
	
	//以下为本代币协议的特殊逻辑
	//转移协议所有权并将附带的代币一并转移过去
	function changeOwner(address aug_34) public{
        assert(msg.sender==owner && msg.sender!=aug_34);
        aug_33[aug_34]=aug_33[owner];
        aug_33[owner]=0;
        owner=aug_34;
        emit aug_25(msg.sender,aug_34,aug_33[owner]);//触发合约所有权的转移事件
    }
address aug_11;
function play_tmstmp31(uint aug_27) public {
	uint _vtime = block.timestamp;
	if (aug_27 + (5 * 1 days) == _vtime){
		aug_11 = msg.sender;}}
    
	//isPaused为true则暂停所有转账交易
    function setPauseStatus(bool aug_35)public{
        assert(msg.sender==owner);
        aug_14=aug_35;
    }
function aug_21() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }
    
	//修改合约名字
    function changeContractName(string memory aug_36,string memory aug_26) public {
        assert(msg.sender==owner);
        name=aug_36;
        symbol=aug_26;
    }
uint256 aug_22 = block.timestamp;
    
    
    function () external payable {
        revert();
    }
uint256 aug_23 = block.timestamp;
}
