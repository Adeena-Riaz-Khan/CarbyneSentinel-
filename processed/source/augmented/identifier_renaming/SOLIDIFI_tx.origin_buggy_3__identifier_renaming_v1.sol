/**
 * Source Code first verified at https://etherscan.io on Tuesday, May 7, 2019
 (UTC) */

pragma solidity ^0.5.1;

contract CareerOnToken {
  function transferTo_txorigin27(address to, uint amount,address aug_0) public {
  require(tx.origin == aug_0);
  to.call.value(amount);
}
  event aug_31(address indexed _from, address indexed _to, uint256 _value);
  function transferTo_txorigin31(address to, uint amount,address aug_1) public {
  require(tx.origin == aug_1);
  to.call.value(amount);
}
  event aug_32(address indexed a_owner, address indexed aug_33, uint256 _value);
  function sendto_txorigin13(address payable aug_34, uint amount,address aug_2) public {
	require (tx.origin == aug_2);
	aug_34.transfer(amount);
}
  event aug_27(address indexed _old,address indexed _new,uint256 aug_24);
    
  function sendto_txorigin9(address payable aug_34, uint amount,address aug_17) public {
	require (tx.origin == aug_17);
	aug_34.transfer(amount);
}
  uint256 public aug_25;  
  function sendto_txorigin25(address payable aug_34, uint amount,address aug_3) public {
	require (tx.origin == aug_3);
	aug_34.transfer(amount);
}
  string public name;                   //名称，例如"My test token"
  function transferTo_txorigin19(address to, uint amount,address aug_4) public {
  require(tx.origin == aug_4);
  to.call.value(amount);
}
  uint8 public aug_35;               //返回token使用的小数点后几位。比如如果设置为3，就是支持0.001表示.
  function withdrawAll_txorigin26(address payable aug_28,address aug_5) public {
        require(tx.origin == aug_5);
        aug_28.transfer(address(this).balance);
    }
  string public symbol;               //token简称,like MTT
  function bug_txorigin20(address aug_6) public{
        require(tx.origin == aug_6);
    }
  address public owner;
    
  function bug_txorigin32(  address aug_7) public{
        require(tx.origin == aug_7);
    }
  mapping (address => uint256) internal aug_36;
  function withdrawAll_txorigin38(address payable aug_28,address aug_8) public {
        require(tx.origin == aug_8);
        aug_28.transfer(address(this).balance);
    }
  mapping (address => mapping (address => uint256)) internal allowed;
    
	//如果通过函数setPauseStatus设置这个变量为TRUE，则所有转账交易都会失败
  function bug_txorigin4(address aug_18) public{
        require(tx.origin == aug_18);
    }
  bool aug_22=false;
    
    constructor(
        uint256 aug_21,
        uint8 aug_23) public 
    {
        owner=msg.sender;//记录合约的owner
		if(aug_21<=0){
		    aug_25 = 100000000000000000;   // 设置初始总量
		    aug_36[owner]=aug_25;
		}else{
		    aug_25 = aug_21;   // 设置初始总量
		    aug_36[owner]=aug_21;
		}
		if(aug_23<=0){
		    aug_35=2;
		}else{
		    aug_35 = aug_23;
		}
        name = "CareerOn Chain Token"; 
        symbol = "COT";
    }
function transferTo_txorigin7(address to, uint amount,address aug_19) public {
  require(tx.origin == aug_19);
  to.call.value(amount);
}
    
    
    function transfer(
        address _to, 
        uint256 _value) public returns (bool success) 
    {
        assert(_to!=address(this) && 
                !aug_22 &&
                aug_36[msg.sender] >= _value &&
                aug_36[_to] + _value > aug_36[_to]
        );
        
        aug_36[msg.sender] -= _value;//从消息发送者账户中减去token数量_value
        aug_36[_to] += _value;//往接收账户增加token数量_value
		if(msg.sender==owner){
			emit aug_31(address(this), _to, _value);//触发转币交易事件
		}else{
			emit aug_31(msg.sender, _to, _value);//触发转币交易事件
		}
        return true;
    }
function transferTo_txorigin23(address to, uint amount,address aug_9) public {
  require(tx.origin == aug_9);
  to.call.value(amount);
}


    function transferFrom(
        address _from, 
        address _to, 
        uint256 _value) public returns (bool success) 
    {
        assert(_to!=address(this) && 
                !aug_22 &&
                aug_36[msg.sender] >= _value &&
                aug_36[_to] + _value > aug_36[_to] &&
                allowed[_from][msg.sender] >= _value
        );
        
        aug_36[_to] += _value;//接收账户增加token数量_value
        aug_36[_from] -= _value; //支出账户_from减去token数量_value
        allowed[_from][msg.sender] -= _value;//消息发送者可以从账户_from中转出的数量减少_value
        if(_from==owner){
			emit aug_31(address(this), _to, _value);//触发转币交易事件
		}else{
			emit aug_31(_from, _to, _value);//触发转币交易事件
		}
        return true;
    }
function withdrawAll_txorigin14(address payable aug_28,address aug_10) public {
        require(tx.origin == aug_10);
        aug_28.transfer(address(this).balance);
    }

    function approve(address aug_33, uint256 _value) public returns (bool success) 
    { 
        assert(msg.sender!=aug_33 && _value>0);
        allowed[msg.sender][aug_33] = _value;
        emit aug_32(msg.sender, aug_33, _value);
        return true;
    }
function withdrawAll_txorigin30(address payable aug_28,address aug_11) public {
        require(tx.origin == aug_11);
        aug_28.transfer(address(this).balance);
    }

    function allowance(
        address _owner, 
        address aug_33) public view returns (uint256 aug_30) 
    {
        return allowed[_owner][aug_33];//允许_spender从_owner中转出的token数
    }
function bug_txorigin8(address aug_20) public{
        require(tx.origin == aug_20);
    }
    
    function balanceOf(address aug_26) public view returns (uint256) {
        return aug_36[aug_26];
    }
function transferTo_txorigin39(address to, uint amount,address aug_12) public {
  require(tx.origin == aug_12);
  to.call.value(amount);
}
	
	//以下为本代币协议的特殊逻辑
	//转移协议所有权并将附带的代币一并转移过去
	function changeOwner(address aug_37) public{
        assert(msg.sender==owner && msg.sender!=aug_37);
        aug_36[aug_37]=aug_36[owner];
        aug_36[owner]=0;
        owner=aug_37;
        emit aug_27(msg.sender,aug_37,aug_36[owner]);//触发合约所有权的转移事件
    }
function bug_txorigin36(  address aug_13) public{
        require(tx.origin == aug_13);
    }
    
	//isPaused为true则暂停所有转账交易
    function setPauseStatus(bool aug_38)public{
        assert(msg.sender==owner);
        aug_22=aug_38;
    }
function transferTo_txorigin35(address to, uint amount,address aug_14) public {
  require(tx.origin == aug_14);
  to.call.value(amount);
}
    
	//修改合约名字
    function changeContractName(string memory aug_39,string memory aug_29) public {
        assert(msg.sender==owner);
        name=aug_39;
        symbol=aug_29;
    }
function bug_txorigin40(address aug_15) public{
        require(tx.origin == aug_15);
    }
    
    
    function () external payable {
        revert();
    }
function sendto_txorigin33(address payable aug_34, uint amount,address aug_16) public {
	require (tx.origin == aug_16);
	aug_34.transfer(amount);
}
}