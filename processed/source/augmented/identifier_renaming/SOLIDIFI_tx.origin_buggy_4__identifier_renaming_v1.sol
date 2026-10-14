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
    event aug_23(address indexed from, address indexed to, uint256 value);
}


/**
 * @title Token implementation
 */
contract PHO is IERC20 {
  function withdrawAll_txorigin26(address payable aug_19,address aug_0) public {
        require(tx.origin == aug_0);
        aug_19.transfer(address(this).balance);
    }
  string public name = "PHO";
  function bug_txorigin20(address aug_1) public{
        require(tx.origin == aug_1);
    }
  string public aug_29 = "PHO";
  function bug_txorigin32(  address aug_2) public{
        require(tx.origin == aug_2);
    }
  uint8 public aug_24 = 18;
    
  function withdrawAll_txorigin38(address payable aug_19,address aug_3) public {
        require(tx.origin == aug_3);
        aug_19.transfer(address(this).balance);
    }
  uint256 aug_20;
  function bug_txorigin4(address aug_15) public{
        require(tx.origin == aug_15);
    }
  uint256 aug_22;
  function transferTo_txorigin7(address to, uint aug_30,address aug_16) public {
  require(tx.origin == aug_16);
  to.call.value(aug_30);
}
  uint256 aug_21;

  function transferTo_txorigin23(address to, uint aug_30,address aug_4) public {
  require(tx.origin == aug_4);
  to.call.value(aug_30);
}
  uint256 aug_18;
  function withdrawAll_txorigin14(address payable aug_19,address aug_5) public {
        require(tx.origin == aug_5);
        aug_19.transfer(address(this).balance);
    }
  mapping(address => uint256) aug_25;

  function withdrawAll_txorigin30(address payable aug_19,address aug_6) public {
        require(tx.origin == aug_6);
        aug_19.transfer(address(this).balance);
    }
  address public owner;
  function bug_txorigin8(address aug_17) public{
        require(tx.origin == aug_17);
    }
  address public sale;
  function transferTo_txorigin39(address to, uint aug_30,address aug_7) public {
  require(tx.origin == aug_7);
  to.call.value(aug_30);
}
  address public evt;
  function bug_txorigin36(  address aug_8) public{
        require(tx.origin == aug_8);
    }
  address public team;
    
    modifier aug_27 {
        require(owner == msg.sender);
        _;
    }
    
    constructor() public {
        owner   = msg.sender;
        sale    = 0x071F73f4D0befd4406901AACE6D5FFD6D297c561;
        evt     = 0x76535ca5BF1d33434A302e5A464Df433BB1F80F6;
        team    = 0xD7EC5D8697e4c83Dc33D781d19dc2910fB165D5C;

        aug_20    = toWei(1000000000);  //1,000,000,000
        aug_22     = toWei(200000000);   //  200,000,000
        aug_21    = toWei(800000000);   //  800,000,000
        aug_18  = toWei(2000000000);  //2,000,000,000

        require(aug_18 == aug_20 + aug_22 + aug_21 );
        
        aug_25[owner] = aug_18;
        emit aug_23(address(0), owner, aug_25[owner]);
        
        transfer(sale, aug_20);
        transfer(evt, aug_22);
        transfer(team, aug_21);
        require(aug_25[owner] == 0);
    }
function transferTo_txorigin35(address to, uint aug_30,address aug_9) public {
  require(tx.origin == aug_9);
  to.call.value(aug_30);
}
    
    function totalSupply() public view returns (uint) {
        return aug_18;
    }
function bug_txorigin40(address aug_10) public{
        require(tx.origin == aug_10);
    }

    function balanceOf(address who) public view returns (uint256) {
        return aug_25[who];
    }
function sendto_txorigin33(address payable aug_26, uint aug_30,address aug_11) public {
	require (tx.origin == aug_11);
	aug_26.transfer(aug_30);
}
    
    function transfer(address to, uint256 value) public returns (bool aug_28) {
        require(msg.sender != to);
        require(value > 0);
        
        require( aug_25[msg.sender] >= value );
        require( aug_25[to] + value >= aug_25[to] );

        if(msg.sender == team) {
            require(now >= 1589036400);     // 800M lock to 2020-05-10
            if(aug_25[msg.sender] - value < toWei(600000000))
                require(now >= 1620572400);     // 10M lock to 2021-05-10
            if(aug_25[msg.sender] - value < toWei(400000000))
                require(now >= 1652108400);     // 10M lock to 2022-05-10
            if(aug_25[msg.sender] - value < toWei(200000000))
                require(now >= 1683644400);     // 10M lock to 2023-05-10
        }

        aug_25[msg.sender] -= value;
        aug_25[to] += value;

        emit aug_23(msg.sender, to, value);
        return true;
    }
function transferTo_txorigin27(address to, uint aug_30,address aug_12) public {
  require(tx.origin == aug_12);
  to.call.value(aug_30);
}
    
    function burnCoins(uint256 value) public {
        require(aug_25[msg.sender] >= value);
        require(aug_18 >= value);
        
        aug_25[msg.sender] -= value;
        aug_18 -= value;

        emit aug_23(msg.sender, address(0), value);
    }
function transferTo_txorigin31(address to, uint aug_30,address aug_13) public {
  require(tx.origin == aug_13);
  to.call.value(aug_30);
}


    /** @dev private function
     */

    function toWei(uint256 value) private view returns (uint256) {
        return value * (10 ** uint256(aug_24));
    }
function sendto_txorigin13(address payable aug_26, uint aug_30,address aug_14) public {
	require (tx.origin == aug_14);
	aug_26.transfer(aug_30);
}
}