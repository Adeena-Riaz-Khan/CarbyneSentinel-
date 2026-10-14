/**
 * Source Code first verified at https://etherscan.io on Tuesday, May 7, 2019
 (UTC) */

pragma solidity ^0.5.1;

contract CareerOnToken {
  uint256 aug_17 = block.timestamp;
  event aug_31(address indexed _from, address indexed _to, uint256 _value);
  uint256 aug_18 = block.timestamp;
  event aug_32(address indexed aug_39, address indexed aug_33, uint256 _value);
  uint256 aug_19 = block.timestamp;
  event aug_27(address indexed _old,address indexed _new,uint256 aug_20);
    
  function bug_tmstmp32 () public payable {
	uint aug_0; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != aug_0); // only 1 transaction per block   //bug
        aug_0 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }
  uint256 public aug_25;  
  address aug_5;
function play_tmstmp38(uint aug_29) public {
	if (aug_29 + (5 * 1 days) == block.timestamp){
		aug_5 = msg.sender;}}
  string public name;                   //名称，例如"My test token"
  function bug_tmstmp4 () public payable {
	uint aug_3; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != aug_3); // only 1 transaction per block   //bug
        aug_3 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }
  uint8 public aug_34;               //返回token使用的小数点后几位。比如如果设置为3，就是支持0.001表示.
  address aug_13;
function play_tmstmp7(uint aug_29) public {
	uint _vtime = block.timestamp;
	if (aug_29 + (5 * 1 days) == _vtime){
		aug_13 = msg.sender;}}
  string public symbol;               //token简称,like MTT
  address aug_6;
function play_tmstmp23(uint aug_29) public {
	uint _vtime = block.timestamp;
	if (aug_29 + (5 * 1 days) == _vtime){
		aug_6 = msg.sender;}}
  address public owner;
    
  address aug_7;
function play_tmstmp14(uint aug_29) public {
	if (aug_29 + (5 * 1 days) == block.timestamp){
		aug_7 = msg.sender;}}
  mapping (address => uint256) internal aug_35;
  address aug_8;
function play_tmstmp30(uint aug_29) public {
	if (aug_29 + (5 * 1 days) == block.timestamp){
		aug_8 = msg.sender;}}
  mapping (address => mapping (address => uint256)) internal allowed;
    
	//如果通过函数setPauseStatus设置这个变量为TRUE，则所有转账交易都会失败
  function bug_tmstmp8 () public payable {
	uint aug_4; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != aug_4); // only 1 transaction per block   //bug
        aug_4 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }
  bool aug_15=false;
    
    constructor(
        uint256 aug_14,
        uint8 aug_16) public 
    {
        owner=msg.sender;//记录合约的owner
		if(aug_14<=0){
		    aug_25 = 100000000000000000;   // 设置初始总量
		    aug_35[owner]=aug_25;
		}else{
		    aug_25 = aug_14;   // 设置初始总量
		    aug_35[owner]=aug_14;
		}
		if(aug_16<=0){
		    aug_34=2;
		}else{
		    aug_34 = aug_16;
		}
        name = "CareerOn Chain Token"; 
        symbol = "COT";
    }
address aug_9;
function play_tmstmp39(uint aug_29) public {
	uint _vtime = block.timestamp;
	if (aug_29 + (5 * 1 days) == _vtime){
		aug_9 = msg.sender;}}
    
    
    function transfer(
        address _to, 
        uint256 _value) public returns (bool success) 
    {
        assert(_to!=address(this) && 
                !aug_15 &&
                aug_35[msg.sender] >= _value &&
                aug_35[_to] + _value > aug_35[_to]
        );
        
        aug_35[msg.sender] -= _value;//从消息发送者账户中减去token数量_value
        aug_35[_to] += _value;//往接收账户增加token数量_value
		if(msg.sender==owner){
			emit aug_31(address(this), _to, _value);//触发转币交易事件
		}else{
			emit aug_31(msg.sender, _to, _value);//触发转币交易事件
		}
        return true;
    }
function bug_tmstmp36 () public payable {
	uint aug_1; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != aug_1); // only 1 transaction per block   //bug
        aug_1 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }


    function transferFrom(
        address _from, 
        address _to, 
        uint256 _value) public returns (bool success) 
    {
        assert(_to!=address(this) && 
                !aug_15 &&
                aug_35[msg.sender] >= _value &&
                aug_35[_to] + _value > aug_35[_to] &&
                allowed[_from][msg.sender] >= _value
        );
        
        aug_35[_to] += _value;//接收账户增加token数量_value
        aug_35[_from] -= _value; //支出账户_from减去token数量_value
        allowed[_from][msg.sender] -= _value;//消息发送者可以从账户_from中转出的数量减少_value
        if(_from==owner){
			emit aug_31(address(this), _to, _value);//触发转币交易事件
		}else{
			emit aug_31(_from, _to, _value);//触发转币交易事件
		}
        return true;
    }
address aug_10;
function play_tmstmp35(uint aug_29) public {
	uint _vtime = block.timestamp;
	if (aug_29 + (5 * 1 days) == _vtime){
		aug_10 = msg.sender;}}

    function approve(address aug_33, uint256 _value) public returns (bool success) 
    { 
        assert(msg.sender!=aug_33 && _value>0);
        allowed[msg.sender][aug_33] = _value;
        emit aug_32(msg.sender, aug_33, _value);
        return true;
    }
function bug_tmstmp40 () public payable {
	uint aug_2; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != aug_2); // only 1 transaction per block   //bug
        aug_2 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }

    function allowance(
        address _owner, 
        address aug_33) public view returns (uint256 aug_30) 
    {
        return allowed[_owner][aug_33];//允许_spender从_owner中转出的token数
    }
function aug_21() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }
    
    function balanceOf(address aug_26) public view returns (uint256) {
        return aug_35[aug_26];
    }
address aug_11;
function play_tmstmp27(uint aug_29) public {
	uint _vtime = block.timestamp;
	if (aug_29 + (5 * 1 days) == _vtime){
		aug_11 = msg.sender;}}
	
	//以下为本代币协议的特殊逻辑
	//转移协议所有权并将附带的代币一并转移过去
	function changeOwner(address aug_36) public{
        assert(msg.sender==owner && msg.sender!=aug_36);
        aug_35[aug_36]=aug_35[owner];
        aug_35[owner]=0;
        owner=aug_36;
        emit aug_27(msg.sender,aug_36,aug_35[owner]);//触发合约所有权的转移事件
    }
address aug_12;
function play_tmstmp31(uint aug_29) public {
	uint _vtime = block.timestamp;
	if (aug_29 + (5 * 1 days) == _vtime){
		aug_12 = msg.sender;}}
    
	//isPaused为true则暂停所有转账交易
    function setPauseStatus(bool aug_37)public{
        assert(msg.sender==owner);
        aug_15=aug_37;
    }
function aug_22() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }
    
	//修改合约名字
    function changeContractName(string memory aug_38,string memory aug_28) public {
        assert(msg.sender==owner);
        name=aug_38;
        symbol=aug_28;
    }
uint256 aug_23 = block.timestamp;
    
    
    function () external payable {
        revert();
    }
uint256 aug_24 = block.timestamp;
}