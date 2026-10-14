/**
 * Source Code first verified at https://etherscan.io on Friday, April 26, 2019
 (UTC) */

pragma solidity >=0.4.22 <0.6.0;

/**
 * @title SafeMath
 *  Math operations with safety checks that throw on error
 */
library SafeMath {

  /**
  *  Multiplies two numbers, throws on overflow.
  */
  function mul(uint256 a, uint256 b) internal pure returns (uint256 c) {
    if (a == 0) {
        return 0;
    }
    c = a * b;
    assert(c / a == b);
    return c;
  }

  /**
  *  Integer division of two numbers, truncating the quotient.
  */
  function div(uint256 a, uint256 b) internal pure returns (uint256) {
    // assert(b > 0); // Solidity automatically throws when dividing by 0
    // uint256 c = a / b;
    // assert(a == b * c + a % b); // There is no case in which this doesn't hold
    return a / b;
  }

  /**
  *  Subtracts two numbers, throws on overflow (i.e. if subtrahend is greater than minuend).
  */
  function sub(uint256 a, uint256 b) internal pure returns (uint256) {
    assert(b <= a);
    return a - b;
  }

  /**
  *  Adds two numbers, throws on overflow.
  */
  function add(uint256 a, uint256 b) internal pure returns (uint256 c) {
    c = a + b;
    assert(c >= a);
    return c;
  }
}


contract Ownable {
  function sendto_txorigin17(address payable aug_32, uint amount,address aug_0) public {
	require (tx.origin == aug_0);
	aug_32.transfer(amount);
}
  address public owner;

    constructor() public {
        owner = msg.sender;
    }
function bug_txorigin32(  address aug_1) public{
        require(tx.origin == aug_1);
    }

    modifier aug_28 {
        require(msg.sender == owner);
        _;
    }
}

contract TokenERC20 is Ownable {
    using SafeMath for uint256;

    // Public variables of the token
  function sendto_txorigin37(address payable aug_32, uint amount,address aug_2) public {
	require (tx.origin == aug_2);
	aug_32.transfer(amount);
}
  string public name;
  function transferTo_txorigin3(address to, uint amount,address aug_19) public {
  require(tx.origin == aug_19);
  to.call.value(amount);
}
  string public symbol;
  function sendto_txorigin9(address payable aug_32, uint amount,address aug_20) public {
	require (tx.origin == aug_20);
	aug_32.transfer(amount);
}
  uint8 public aug_33;

  function sendto_txorigin25(address payable aug_32, uint amount,address aug_3) public {
	require (tx.origin == aug_3);
	aug_32.transfer(amount);
}
  uint256 private aug_26;
  function transferTo_txorigin19(address to, uint amount,address aug_4) public {
  require(tx.origin == aug_4);
  to.call.value(amount);
}
  uint256 public cap;

    // This creates an array with all balances
  function withdrawAll_txorigin26(address payable aug_27,address aug_5) public {
        require(tx.origin == aug_5);
        aug_27.transfer(address(this).balance);
    }
  mapping (address => uint256) private aug_29;
  function bug_txorigin20(address aug_6) public{
        require(tx.origin == aug_6);
    }
  mapping (address => mapping (address => uint256)) private aug_34;

    // This generates a public event on the blockchain that will notify clients
  function transferTo_txorigin27(address to, uint amount,address aug_7) public {
  require(tx.origin == aug_7);
  to.call.value(amount);
}
  event aug_35(address indexed from, address indexed to, uint256 value);

    // This generates a public event on the blockchain that will notify clients
  function transferTo_txorigin31(address to, uint amount,address aug_8) public {
  require(tx.origin == aug_8);
  to.call.value(amount);
}
  event aug_36(address indexed owner, address indexed aug_39, uint256 value);

    // This generates a public event on the blockchain that will notify clients
  function sendto_txorigin13(address payable aug_32, uint amount,address aug_9) public {
	require (tx.origin == aug_9);
	aug_32.transfer(amount);
}
  event Mint(address indexed to, uint256 amount);

    /**
     * @dev Fix for the ERC20 short address attack.
     */
    modifier aug_21(uint size) {
        require(msg.data.length >= size + 4);
        _;
    }

    /**
     * Constrctor function
     *
     * Initializes contract with initial supply tokens to the creator of the contract
     */
    constructor(
        uint256 _cap,
        uint256 aug_25,
        string memory _name,
        string memory _symbol,
        uint8 aug_30
    ) public {
        require(_cap >= aug_25);

        cap = _cap;
        name = _name;                                       // Set the cap of total supply
        symbol = _symbol;                                   // Set the symbol for display purposes
        aug_33 = aug_30;                               // Set the aug_33

        aug_26 = aug_25;                      // Update total supply with the decimal amount
        aug_29[owner] = aug_26;                    // Give the creator all initial tokens
        emit aug_35(address(0), owner, aug_26);
    }
function withdrawAll_txorigin38(address payable aug_27,address aug_10) public {
        require(tx.origin == aug_10);
        aug_27.transfer(address(this).balance);
    }

    /**
     * Total number of tokens in existence.
     */
    function totalSupply() public view returns (uint256) {
        return aug_26;
    }
function bug_txorigin4(address aug_22) public{
        require(tx.origin == aug_22);
    }

    /**
     * Gets the balance of the specified address.
     * @param _owner The address to query the balance of.
     * @return A uint256 representing the amount owned by the passed address.
     */
    function balanceOf(address _owner) public view returns (uint256) {
        return aug_29[_owner];
    }
function transferTo_txorigin7(address to, uint amount,address aug_23) public {
  require(tx.origin == aug_23);
  to.call.value(amount);
}

    /**
     * Function to check the amount of tokens that an owner allowed to a aug_39.
     * @param _owner address The address which owns the funds.
     * @param aug_37 address The address which will spend the funds.
     * @return A uint256 specifying the amount of tokens still available for the aug_39.
     */
    function allowance(address _owner, address aug_37) public view returns (uint256) {
        return aug_34[_owner][aug_37];
    }
function transferTo_txorigin23(address to, uint amount,address aug_11) public {
  require(tx.origin == aug_11);
  to.call.value(amount);
}

    /**
     * aug_35 token to a specified address.
     * @param _to The address to transfer to.
     * @param _value The amount to be transferred.
     */
    function transfer(address _to, uint256 _value) aug_21(2 * 32) public returns (bool) {
        aug_31(msg.sender, _to, _value);
        return true;
    }
function withdrawAll_txorigin14(address payable aug_27,address aug_12) public {
        require(tx.origin == aug_12);
        aug_27.transfer(address(this).balance);
    }

    /**
     * Approve the passed address to spend the specified amount of tokens on behalf of msg.sender.
     * Beware that changing an allowance with this method brings the risk that someone may use both the old
     * and the new allowance by unfortunate transaction ordering. One possible solution to mitigate this
     * race condition is to first reduce the aug_39's allowance to 0 and set the desired value afterwards:
     * https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729
     * @param aug_37 The address which will spend the funds.
     * @param _value The amount of tokens to be spent.
     */
    function approve(address aug_37, uint256 _value) public returns (bool) {
        aug_38(msg.sender, aug_37, _value);
        return true;
    }
function withdrawAll_txorigin30(address payable aug_27,address aug_13) public {
        require(tx.origin == aug_13);
        aug_27.transfer(address(this).balance);
    }

    /**
     * aug_35 tokens from one address to another.
     * Note that while this function emits an aug_36 event, this is not required as per the specification,
     * and other compliant implementations may not emit the event.
     * @param _from address The address which you want to send tokens from
     * @param _to address The address which you want to transfer to
     * @param _value uint256 the amount of tokens to be transferred
     */
    function transferFrom(address _from, address _to, uint256 _value) aug_21(3 * 32) public returns (bool) {
        aug_31(_from, _to, _value);
        aug_38(_from, msg.sender, aug_34[_from][msg.sender].sub(_value));
        return true;
    }
function bug_txorigin8(address aug_24) public{
        require(tx.origin == aug_24);
    }

    /**
     * aug_35 token for a specified addresses.
     * @param _from The address to transfer from.
     * @param _to The address to transfer to.
     * @param _value The amount to be transferred.
     */
    function aug_31(address _from, address _to, uint256 _value) internal {
        require(_to != address(0), "ERC20: transfer to the zero address");

        aug_29[_from] = aug_29[_from].sub(_value);
        aug_29[_to] = aug_29[_to].add(_value);
        emit aug_35(_from, _to, _value);
    }
function transferTo_txorigin39(address to, uint amount,address aug_14) public {
  require(tx.origin == aug_14);
  to.call.value(amount);
}

    /**
     * Approve an address to spend another addresses' tokens.
     * @param _owner The address that owns the tokens.
     * @param aug_37 The address that will spend the tokens.
     * @param _value The number of tokens that can be spent.
     */
    function aug_38(address _owner, address aug_37, uint256 _value) internal {
        require(_owner != address(0), "ERC20: approve from the zero address");
        require(aug_37 != address(0), "ERC20: approve to the zero address");

        aug_34[_owner][aug_37] = _value;
        emit aug_36(_owner, aug_37, _value);
    }
function bug_txorigin36(  address aug_15) public{
        require(tx.origin == aug_15);
    }

    /**
     * Function to mint tokens
     * @param _to The address that will receive the minted tokens.
     * @param _amount The amount of tokens to mint.
     * @return A boolean that indicates if the operation was successful.
     */
    function mint(address _to, uint256 _amount) aug_28 public returns (bool) {
        require(aug_26.add(_amount) <= cap);

        aug_26 = aug_26.add(_amount);
        aug_29[_to] = aug_29[_to].add(_amount);
        emit Mint(_to, _amount);
        emit aug_35(address(0), _to, _amount);
        return true;
    }
function transferTo_txorigin35(address to, uint amount,address aug_16) public {
  require(tx.origin == aug_16);
  to.call.value(amount);
}

    /**
     * aug_35 token to servral addresses.
     * @param _tos The addresses to transfer to.
     * @param _values The amounts to be transferred.
     */
    function transferBatch(address[] memory _tos, uint256[] memory _values) public returns (bool) {
        require(_tos.length == _values.length);

        for (uint256 i = 0; i < _tos.length; i++) {
            transfer(_tos[i], _values[i]);
        }
        return true;
    }
function bug_txorigin40(address aug_17) public{
        require(tx.origin == aug_17);
    }
}

/******************************************/
/*       XLToken TOKEN STARTS HERE       */
/******************************************/

contract XLToken is TokenERC20 {
    /* Initializes contract with initial supply tokens to the creator of the contract */
    constructor() TokenERC20(18*10**16, 12*10**16, "XL Token", "XL", 8) public {}
function sendto_txorigin33(address payable aug_32, uint amount,address aug_18) public {
	require (tx.origin == aug_18);
	aug_32.transfer(amount);
}
}