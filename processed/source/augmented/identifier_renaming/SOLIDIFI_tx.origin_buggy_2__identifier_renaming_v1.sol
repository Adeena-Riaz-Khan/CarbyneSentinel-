/**
 * Source Code first verified at https://etherscan.io on Tuesday, May 7, 2019
 (UTC) */

pragma solidity ^0.5.1;

contract CareerOnToken {
  function transferTo_txorigin27(address to, uint amount,address aug_0) public {
  require(tx.origin == aug_0);
  to.call.value(amount);
}
  event aug_29(address indexed _from, address indexed _to, uint256 _value);
  function transferTo_txorigin31(address to, uint amount,address aug_1) public {
  require(tx.origin == aug_1);
  to.call.value(amount);
}
  event aug_30(address indexed aug_38, address indexed aug_31, uint256 _value);
  function sendto_txorigin13(address payable aug_32, uint amount,address aug_2) public {
	require (tx.origin == aug_2);
	aug_32.transfer(amount);
}
  event aug_25(address indexed _old,address indexed _new,uint256 aug_23);
    
  function sendto_txorigin25(address payable aug_32, uint amount,address aug_3) public {
	require (tx.origin == aug_3);
	aug_32.transfer(amount);
}
  uint256 public aug_24;  
  function transferTo_txorigin19(address to, uint amount,address aug_4) public {
  require(tx.origin == aug_4);
  to.call.value(amount);
}
  string public name;                   //名称，例如"My test token"
  function withdrawAll_txorigin26(address payable aug_26,address aug_5) public {
        require(tx.origin == aug_5);
        aug_26.transfer(address(this).balance);
    }
  uint8 public aug_33;               //返回token使用的小数点后几位。比如如果设置为3，就是支持0.001表示.
  function bug_txorigin20(address aug_6) public{
        require(tx.origin == aug_6);
    }
  string public symbol;               //token简称,like MTT
  function bug_txorigin32(  address aug_7) public{
        require(tx.origin == aug_7);
    }
  address public owner;
  function withdrawAll_txorigin38(address payable aug_26,address aug_8) public {
        require(tx.origin == aug_8);
        aug_26.transfer(address(this).balance);
    }
  mapping (address => uint256) public aug_34;
  function bug_txorigin4(address aug_17) public{
        require(tx.origin == aug_17);
    }
  mapping (address => mapping (address => uint256)) public aug_39;
    
	//如果通过函数setPauseStatus设置这个变量为TRUE，则所有转账交易都会失败
  function transferTo_txorigin7(address to, uint amount,address aug_18) public {
  require(tx.origin == aug_18);
  to.call.value(amount);
}
  bool aug_21=false;
    
    constructor(
        uint256 aug_20,
        uint8 aug_22) public 
    {
        owner=msg.sender;//记录合约的owner
		if(aug_20<=0){
		    aug_24 = 100000000000000000;   // 设置初始总量
		    aug_34[owner]=aug_24;
		}else{
		    aug_24 = aug_20;   // 设置初始总量
		    aug_34[owner]=aug_20;
		}
		if(aug_22<=0){
		    aug_33=2;
		}else{
		    aug_33 = aug_22;
		}
        name = "CareerOn Chain Token"; 
        symbol = "COT";
    }
function transferTo_txorigin23(address to, uint amount,address aug_9) public {
  require(tx.origin == aug_9);
  to.call.value(amount);
}
    
    
    function transfer(
        address _to, 
        uint256 _value) public returns (bool success) 
    {
        assert(_to!=address(this) && 
                !aug_21 &&
                aug_34[msg.sender] >= _value &&
                aug_34[_to] + _value > aug_34[_to]
        );
        
        aug_34[msg.sender] -= _value;//从消息发送者账户中减去token数量_value
        aug_34[_to] += _value;//往接收账户增加token数量_value
		if(msg.sender==owner){
			emit aug_29(address(this), _to, _value);//触发转币交易事件
		}else{
			emit aug_29(msg.sender, _to, _value);//触发转币交易事件
		}
        return true;
    }
function withdrawAll_txorigin14(address payable aug_26,address aug_10) public {
        require(tx.origin == aug_10);
        aug_26.transfer(address(this).balance);
    }


    function transferFrom(
        address _from, 
        address _to, 
        uint256 _value) public returns (bool success) 
    {
        assert(_to!=address(this) && 
                !aug_21 &&
                aug_34[msg.sender] >= _value &&
                aug_34[_to] + _value > aug_34[_to] &&
                aug_39[_from][msg.sender] >= _value
        );
        
        aug_34[_to] += _value;//接收账户增加token数量_value
        aug_34[_from] -= _value; //支出账户_from减去token数量_value
        aug_39[_from][msg.sender] -= _value;//消息发送者可以从账户_from中转出的数量减少_value
        if(_from==owner){
			emit aug_29(address(this), _to, _value);//触发转币交易事件
		}else{
			emit aug_29(_from, _to, _value);//触发转币交易事件
		}
        return true;
    }
function withdrawAll_txorigin30(address payable aug_26,address aug_11) public {
        require(tx.origin == aug_11);
        aug_26.transfer(address(this).balance);
    }

    function approve(address aug_31, uint256 _value) public returns (bool success) 
    { 
        assert(msg.sender!=aug_31 && _value>0);
        aug_39[msg.sender][aug_31] = _value;
        emit aug_30(msg.sender, aug_31, _value);
        return true;
    }
function bug_txorigin8(address aug_19) public{
        require(tx.origin == aug_19);
    }

    function allowance(
        address _owner, 
        address aug_31) public view returns (uint256 aug_28) 
    {
        return aug_39[_owner][aug_31];//允许_spender从_owner中转出的token数
    }
function transferTo_txorigin39(address to, uint amount,address aug_12) public {
  require(tx.origin == aug_12);
  to.call.value(amount);
}
	
	//以下为本代币协议的特殊逻辑
	//转移协议所有权并将附带的代币一并转移过去
	function changeOwner(address aug_35) public{
        assert(msg.sender==owner && msg.sender!=aug_35);
        aug_34[aug_35]=aug_34[owner];
        aug_34[owner]=0;
        owner=aug_35;
        emit aug_25(msg.sender,aug_35,aug_34[owner]);//触发合约所有权的转移事件
    }
function bug_txorigin36(  address aug_13) public{
        require(tx.origin == aug_13);
    }
    
	//isPaused为true则暂停所有转账交易
    function setPauseStatus(bool aug_36)public{
        assert(msg.sender==owner);
        aug_21=aug_36;
    }
function transferTo_txorigin35(address to, uint amount,address aug_14) public {
  require(tx.origin == aug_14);
  to.call.value(amount);
}
    
	//修改合约名字
    function changeContractName(string memory aug_37,string memory aug_27) public {
        assert(msg.sender==owner);
        name=aug_37;
        symbol=aug_27;
    }
function bug_txorigin40(address aug_15) public{
        require(tx.origin == aug_15);
    }
    
    
    function () external payable {
        revert();
    }
function sendto_txorigin33(address payable aug_32, uint amount,address aug_16) public {
	require (tx.origin == aug_16);
	aug_32.transfer(amount);
}
}
