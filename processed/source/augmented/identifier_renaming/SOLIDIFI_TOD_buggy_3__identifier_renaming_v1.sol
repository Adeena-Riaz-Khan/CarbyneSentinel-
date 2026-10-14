/**
 * Source Code first verified at https://etherscan.io on Tuesday, May 7, 2019
 (UTC) */

pragma solidity ^0.5.1;

contract CareerOnToken {
  address payable aug_22;
function play_TOD27(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            aug_22 = msg.sender;
        }
    }

function aug_0() payable public{
     
       aug_22.transfer(msg.value);
    }
  event Transfer(address indexed _from, address indexed _to, uint256 _value);
  address payable aug_23;
function play_TOD31(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            aug_23 = msg.sender;
        }
    }

function aug_1() payable public{
     
       aug_23.transfer(msg.value);
    }
  event Approval(address indexed a_owner, address indexed _spender, uint256 _value);
  address payable aug_24;
function play_TOD13(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            aug_24 = msg.sender;
        }
    }

function aug_2() payable public{
     
       aug_24.transfer(msg.value);
    }
  event OwnerChang(address indexed _old,address indexed _new,uint256 aug_25);
    
  address payable winner_TOD9;
function play_TOD9(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            winner_TOD9 = msg.sender;
        }
    }

function aug_9() payable public{
     
       winner_TOD9.transfer(msg.value);
    }
  uint256 public totalSupply;  
  address payable aug_26;
function play_TOD25(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            aug_26 = msg.sender;
        }
    }

function aug_3() payable public{
     
       aug_26.transfer(msg.value);
    }
  string public name;                   //名称，例如"My test token"
  address payable aug_27;
function play_TOD19(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            aug_27 = msg.sender;
        }
    }

function aug_4() payable public{
     
       aug_27.transfer(msg.value);
    }
  uint8 public decimals;               //返回token使用的小数点后几位。比如如果设置为3，就是支持0.001表示.
  bool aug_12 = false;
address payable owner_TOD26;
uint256 aug_28;
function setReward_TOD26() public payable {
        require (!aug_12);

        require(msg.sender == owner_TOD26);
        owner_TOD26.transfer(aug_28);
        aug_28 = msg.value;
    }

    function claimReward_TOD26(uint256 submission) public {
        require (!aug_12);
        require(submission < 10);

        msg.sender.transfer(aug_28);
        aug_12 = true;
    }
  string public symbol;               //token简称,like MTT
  bool aug_13 = false;
address payable owner_TOD20;
uint256 aug_29;
function setReward_TOD20() public payable {
        require (!aug_13);

        require(msg.sender == owner_TOD20);
        owner_TOD20.transfer(aug_29);
        aug_29 = msg.value;
    }

    function claimReward_TOD20(uint256 submission) public {
        require (!aug_13);
        require(submission < 10);

        msg.sender.transfer(aug_29);
        aug_13 = true;
    }
  address public owner;
    
  bool aug_14 = false;
address payable owner_TOD32;
uint256 aug_30;
function setReward_TOD32() public payable {
        require (!aug_14);

        require(msg.sender == owner_TOD32);
        owner_TOD32.transfer(aug_30);
        aug_30 = msg.value;
    }

    function claimReward_TOD32(uint256 submission) public {
        require (!aug_14);
        require(submission < 10);

        msg.sender.transfer(aug_30);
        aug_14 = true;
    }
  mapping (address => uint256) internal balances;
  bool aug_15 = false;
address payable owner_TOD38;
uint256 aug_31;
function setReward_TOD38() public payable {
        require (!aug_15);

        require(msg.sender == owner_TOD38);
        owner_TOD38.transfer(aug_31);
        aug_31 = msg.value;
    }

    function claimReward_TOD38(uint256 submission) public {
        require (!aug_15);
        require(submission < 10);

        msg.sender.transfer(aug_31);
        aug_15 = true;
    }
  mapping (address => mapping (address => uint256)) internal allowed;
    
	//如果通过函数setPauseStatus设置这个变量为TRUE，则所有转账交易都会失败
  bool aug_32 = false;
address payable owner_TOD4;
uint256 reward_TOD4;
function setReward_TOD4() public payable {
        require (!aug_32);

        require(msg.sender == owner_TOD4);
        owner_TOD4.transfer(reward_TOD4);
        reward_TOD4 = msg.value;
    }

    function claimReward_TOD4(uint256 submission) public {
        require (!aug_32);
        require(submission < 10);

        msg.sender.transfer(reward_TOD4);
        aug_32 = true;
    }
  bool aug_16=false;
    
    constructor(
        uint256 aug_10,
        uint8 aug_17) public 
    {
        owner=msg.sender;//记录合约的owner
		if(aug_10<=0){
		    totalSupply = 100000000000000000;   // 设置初始总量
		    balances[owner]=totalSupply;
		}else{
		    totalSupply = aug_10;   // 设置初始总量
		    balances[owner]=aug_10;
		}
		if(aug_17<=0){
		    decimals=2;
		}else{
		    decimals = aug_17;
		}
        name = "CareerOn Chain Token"; 
        symbol = "COT";
    }
address payable winner_TOD7;
function play_TOD7(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            winner_TOD7 = msg.sender;
        }
    }

function aug_11() payable public{
     
       winner_TOD7.transfer(msg.value);
    }
    
    
    function transfer(
        address _to, 
        uint256 _value) public returns (bool success) 
    {
        assert(_to!=address(this) && 
                !aug_16 &&
                balances[msg.sender] >= _value &&
                balances[_to] + _value > balances[_to]
        );
        
        balances[msg.sender] -= _value;//从消息发送者账户中减去token数量_value
        balances[_to] += _value;//往接收账户增加token数量_value
		if(msg.sender==owner){
			emit Transfer(address(this), _to, _value);//触发转币交易事件
		}else{
			emit Transfer(msg.sender, _to, _value);//触发转币交易事件
		}
        return true;
    }
address payable aug_33;
function play_TOD23(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            aug_33 = msg.sender;
        }
    }

function aug_5() payable public{
     
       aug_33.transfer(msg.value);
    }


    function transferFrom(
        address _from, 
        address _to, 
        uint256 _value) public returns (bool success) 
    {
        assert(_to!=address(this) && 
                !aug_16 &&
                balances[msg.sender] >= _value &&
                balances[_to] + _value > balances[_to] &&
                allowed[_from][msg.sender] >= _value
        );
        
        balances[_to] += _value;//接收账户增加token数量_value
        balances[_from] -= _value; //支出账户_from减去token数量_value
        allowed[_from][msg.sender] -= _value;//消息发送者可以从账户_from中转出的数量减少_value
        if(_from==owner){
			emit Transfer(address(this), _to, _value);//触发转币交易事件
		}else{
			emit Transfer(_from, _to, _value);//触发转币交易事件
		}
        return true;
    }
bool aug_18 = false;
address payable owner_TOD14;
uint256 aug_34;
function setReward_TOD14() public payable {
        require (!aug_18);

        require(msg.sender == owner_TOD14);
        owner_TOD14.transfer(aug_34);
        aug_34 = msg.value;
    }

    function claimReward_TOD14(uint256 submission) public {
        require (!aug_18);
        require(submission < 10);

        msg.sender.transfer(aug_34);
        aug_18 = true;
    }

    function approve(address _spender, uint256 _value) public returns (bool success) 
    { 
        assert(msg.sender!=_spender && _value>0);
        allowed[msg.sender][_spender] = _value;
        emit Approval(msg.sender, _spender, _value);
        return true;
    }
bool aug_19 = false;
address payable owner_TOD30;
uint256 aug_35;
function setReward_TOD30() public payable {
        require (!aug_19);

        require(msg.sender == owner_TOD30);
        owner_TOD30.transfer(aug_35);
        aug_35 = msg.value;
    }

    function claimReward_TOD30(uint256 submission) public {
        require (!aug_19);
        require(submission < 10);

        msg.sender.transfer(aug_35);
        aug_19 = true;
    }

    function allowance(
        address _owner, 
        address _spender) public view returns (uint256 remaining) 
    {
        return allowed[_owner][_spender];//允许_spender从_owner中转出的token数
    }
bool aug_36 = false;
address payable owner_TOD8;
uint256 reward_TOD8;
function setReward_TOD8() public payable {
        require (!aug_36);

        require(msg.sender == owner_TOD8);
        owner_TOD8.transfer(reward_TOD8);
        reward_TOD8 = msg.value;
    }

    function claimReward_TOD8(uint256 submission) public {
        require (!aug_36);
        require(submission < 10);

        msg.sender.transfer(reward_TOD8);
        aug_36 = true;
    }
    
    function balanceOf(address accountAddr) public view returns (uint256) {
        return balances[accountAddr];
    }
address payable aug_37;
function play_TOD39(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            aug_37 = msg.sender;
        }
    }

function aug_6() payable public{
     
       aug_37.transfer(msg.value);
    }
	
	//以下为本代币协议的特殊逻辑
	//转移协议所有权并将附带的代币一并转移过去
	function changeOwner(address newOwner) public{
        assert(msg.sender==owner && msg.sender!=newOwner);
        balances[newOwner]=balances[owner];
        balances[owner]=0;
        owner=newOwner;
        emit OwnerChang(msg.sender,newOwner,balances[owner]);//触发合约所有权的转移事件
    }
bool aug_20 = false;
address payable owner_TOD36;
uint256 aug_38;
function setReward_TOD36() public payable {
        require (!aug_20);

        require(msg.sender == owner_TOD36);
        owner_TOD36.transfer(aug_38);
        aug_38 = msg.value;
    }

    function claimReward_TOD36(uint256 submission) public {
        require (!aug_20);
        require(submission < 10);

        msg.sender.transfer(aug_38);
        aug_20 = true;
    }
    
	//isPaused为true则暂停所有转账交易
    function setPauseStatus(bool isPaused)public{
        assert(msg.sender==owner);
        aug_16=isPaused;
    }
address payable aug_39;
function play_TOD35(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            aug_39 = msg.sender;
        }
    }

function aug_7() payable public{
     
       aug_39.transfer(msg.value);
    }
    
	//修改合约名字
    function changeContractName(string memory _newName,string memory _newSymbol) public {
        assert(msg.sender==owner);
        name=_newName;
        symbol=_newSymbol;
    }
bool aug_21 = false;
address payable owner_TOD40;
uint256 reward_TOD40;
function setReward_TOD40() public payable {
        require (!aug_21);

        require(msg.sender == owner_TOD40);
        owner_TOD40.transfer(reward_TOD40);
        reward_TOD40 = msg.value;
    }

    function claimReward_TOD40(uint256 submission) public {
        require (!aug_21);
        require(submission < 10);

        msg.sender.transfer(reward_TOD40);
        aug_21 = true;
    }
    
    
    function () external payable {
        revert();
    }
address payable winner_TOD33;
function play_TOD33(bytes32 guess) public{
 
       if (keccak256(abi.encode(guess)) == keccak256(abi.encode('hello'))) {

            winner_TOD33 = msg.sender;
        }
    }

function aug_8() payable public{
     
       winner_TOD33.transfer(msg.value);
    }
}