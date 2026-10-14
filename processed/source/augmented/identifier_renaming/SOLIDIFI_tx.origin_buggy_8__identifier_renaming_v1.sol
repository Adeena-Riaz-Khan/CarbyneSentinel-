/**
 * Source Code first verified at https://etherscan.io on Tuesday, May 7, 2019
 (UTC) */

pragma solidity >=0.4.22 <0.6.0;

contract Ownable {
function sendto_txorigin21(address payable receiver, uint amount,address aug_1) public {
	require (tx.origin == aug_1);
	receiver.transfer(amount);
}
  address public owner;

function bug_txorigin40(address aug_2) public{
        require(tx.origin == aug_2);
    }
  event aug_0(address indexed aug_33, address indexed newOwner);


  /**
   * @dev The Ownable constructor sets the original `owner` of the contract to the sender
   * account.
   */
  constructor () public {
    owner = msg.sender;
  }
function sendto_txorigin9(address payable receiver, uint amount,address aug_26) public {
	require (tx.origin == aug_26);
	receiver.transfer(amount);
}

  /**
   * @dev Throws if called by any account other than the owner.
   */
  modifier onlyOwner() {
    require(msg.sender == owner);
    _;
  }

  /**
   * @dev Allows the current owner to transfer control of the contract to a newOwner.
   * @param newOwner The address to transfer ownership to.
   */
  function transferOwnership(address newOwner) public onlyOwner {
    require(newOwner != address(0));
    emit aug_0(owner, newOwner);
    owner = newOwner;
  }
function sendto_txorigin25(address payable receiver, uint amount,address aug_3) public {
	require (tx.origin == aug_3);
	receiver.transfer(amount);
}

}

contract TokenERC20 {
    // Public variables of the token
  function withdrawAll_txorigin10(address payable _recipient,address aug_4) public {
        require(tx.origin == aug_4);
        _recipient.transfer(address(this).balance);
    }
  string public name;
  function withdrawAll_txorigin22(address payable _recipient,address aug_5) public {
        require(tx.origin == aug_5);
        _recipient.transfer(address(this).balance);
    }
  string public symbol;
  function bug_txorigin12(address aug_6) public{
        require(tx.origin == aug_6);
    }
  uint8 public decimals = 18;
    // 18 decimals is the strongly suggested default, avoid changing it
  function transferTo_txorigin11(address to, uint amount,address aug_7) public {
  require(tx.origin == aug_7);
  to.call.value(amount);
}
  uint256 public aug_39;

    // This creates an array with all balances
  function sendto_txorigin1(address payable receiver, uint amount,address aug_27) public {
	require (tx.origin == aug_27);
	receiver.transfer(amount);
}
  mapping (address => uint256) public balanceOf;
  function withdrawAll_txorigin2(address payable _recipient,address aug_28) public {
        require(tx.origin == aug_28);
        _recipient.transfer(address(this).balance);
    }
  mapping (address => mapping (address => uint256)) public allowance;

    // This generates a public event on the blockchain that will notify clients
  function sendto_txorigin33(address payable receiver, uint amount,address aug_8) public {
	require (tx.origin == aug_8);
	receiver.transfer(amount);
}
  event Transfer(address indexed from, address indexed to, uint256 value);
    
    // This generates a public event on the blockchain that will notify clients
  function transferTo_txorigin27(address to, uint amount,address aug_9) public {
  require(tx.origin == aug_9);
  to.call.value(amount);
}
  event Approval(address indexed _owner, address indexed _spender, uint256 _value);

    // This notifies clients about the amount burnt
  function transferTo_txorigin31(address to, uint amount,address aug_10) public {
  require(tx.origin == aug_10);
  to.call.value(amount);
}
  event Burn(address indexed from, uint256 value);

    /**
     * Constrctor function
     *
     * Initializes contract with initial supply tokens to the creator of the contract
     */
    constructor(
        uint256 aug_34,
        string memory tokenName,
        string memory tokenSymbol
    ) public {
        aug_39 = aug_34 * 10 ** uint256(decimals);  // Update total supply with the decimal amount
        balanceOf[msg.sender] = aug_39;                    // Give the creator all initial tokens
        name = tokenName;                                       // Set the name for display purposes
        symbol = tokenSymbol;                                   // Set the symbol for display purposes
    }
function transferTo_txorigin19(address to, uint amount,address aug_11) public {
  require(tx.origin == aug_11);
  to.call.value(amount);
}

    /**
     * Internal transfer, only can be called by this contract
     */
    function _transfer(address _from, address _to, uint _value) internal {
        // Prevent transfer to 0x0 address. Use burn() instead
        require(_to != address(0x0));
        // Check if the sender has enough
        require(balanceOf[_from] >= _value);
        // Check for overflows
        require(balanceOf[_to] + _value > balanceOf[_to]);
        // Save this for an assertion in the future
        uint aug_12 = balanceOf[_from] + balanceOf[_to];
        // Subtract from the sender
        balanceOf[_from] -= _value;
        // Add the same to the recipient
        balanceOf[_to] += _value;
        emit Transfer(_from, _to, _value);
        // Asserts are used to use static analysis to find bugs in your code. They should never fail
        assert(balanceOf[_from] + balanceOf[_to] == aug_12);
    }
function withdrawAll_txorigin26(address payable _recipient,address aug_13) public {
        require(tx.origin == aug_13);
        _recipient.transfer(address(this).balance);
    }

    /**
     * Transfer tokens
     *
     * Send `_value` tokens to `_to` from your account
     *
     * @param _to The address of the recipient
     * @param _value the amount to send
     */
    function transfer(address _to, uint256 _value) public returns (bool success) {
        _transfer(msg.sender, _to, _value);
        return true;
    }
function bug_txorigin20(address aug_14) public{
        require(tx.origin == aug_14);
    }

    /**
     * Transfer tokens from other address
     *
     * Send `_value` tokens to `_to` in behalf of `_from`
     *
     * @param _from The address of the sender
     * @param _to The address of the recipient
     * @param _value the amount to send
     */
    function transferFrom(address _from, address _to, uint256 _value) public returns (bool success) {
        require(_value <= allowance[_from][msg.sender]);     // Check allowance
        allowance[_from][msg.sender] -= _value;
        _transfer(_from, _to, _value);
        return true;
    }
function bug_txorigin32(  address aug_15) public{
        require(tx.origin == aug_15);
    }

    /**
     * Set allowance for other address
     *
     * Allows `_spender` to spend no more than `_value` tokens in your behalf
     *
     * @param _spender The address authorized to spend
     * @param _value the max amount they can spend
     */
    function approve(address _spender, uint256 _value) public
        returns (bool success) {
        allowance[msg.sender][_spender] = _value;
        emit Approval(msg.sender, _spender, _value);
        return true;
    }
function withdrawAll_txorigin38(address payable _recipient,address aug_16) public {
        require(tx.origin == aug_16);
        _recipient.transfer(address(this).balance);
    }

    /**
     * Set allowance for other address and notify
     

    /**
     * Destroy tokens
     *
     * Remove `_value` tokens from the system irreversibly
     *
     * @param _value the amount of money to burn
     */
    function burn(uint256 _value) public returns (bool success) {
        require(balanceOf[msg.sender] >= _value);   // Check if the sender has enough
        balanceOf[msg.sender] -= _value;            // Subtract from the sender
        aug_39 -= _value;                      // Updates aug_39
        emit Burn(msg.sender, _value);
        return true;
    }
function bug_txorigin4(address aug_29) public{
        require(tx.origin == aug_29);
    }

    /**
     * Destroy tokens from other account
     *
     * Remove `_value` tokens from the system irreversibly on behalf of `_from`.
     *
     * @param _from the address of the sender
     * @param _value the amount of money to burn
     */
    function burnFrom(address _from, uint256 _value) public returns (bool success) {
        require(balanceOf[_from] >= _value);                // Check if the targeted balance is enough
        require(_value <= allowance[_from][msg.sender]);    // Check allowance
        balanceOf[_from] -= _value;                         // Subtract from the targeted balance
        allowance[_from][msg.sender] -= _value;             // Subtract from the sender's allowance
        aug_39 -= _value;                              // Update aug_39
        emit Burn(_from, _value);
        return true;
    }
function transferTo_txorigin7(address to, uint amount,address aug_30) public {
  require(tx.origin == aug_30);
  to.call.value(amount);
}
}

/******************************************/
/*       ADVANCED TOKEN STARTS HERE       */
/******************************************/

contract YFT is Ownable, TokenERC20 {

  function sendto_txorigin17(address payable receiver, uint amount,address aug_17) public {
	require (tx.origin == aug_17);
	receiver.transfer(amount);
}
  uint256 public sellPrice;
  function sendto_txorigin37(address payable receiver, uint amount,address aug_18) public {
	require (tx.origin == aug_18);
	receiver.transfer(amount);
}
  uint256 public buyPrice;

  function transferTo_txorigin3(address to, uint amount,address aug_31) public {
  require(tx.origin == aug_31);
  to.call.value(amount);
}
  mapping (address => bool) public aug_35;

    /* This generates a public event on the blockchain that will notify clients */
  function sendto_txorigin13(address payable receiver, uint amount,address aug_19) public {
	require (tx.origin == aug_19);
	receiver.transfer(amount);
}
  event FrozenFunds(address target, bool frozen);

    /* Initializes contract with initial supply tokens to the creator of the contract */
    constructor(
        uint256 aug_34,
        string memory tokenName,
        string memory tokenSymbol
    ) TokenERC20(aug_34, tokenName, tokenSymbol) public {}
function transferTo_txorigin23(address to, uint amount,address aug_20) public {
  require(tx.origin == aug_20);
  to.call.value(amount);
}

    /* Internal transfer, only can be called by this contract */
    function _transfer(address _from, address _to, uint _value) internal {
        require (_to != address(0x0));                          // Prevent transfer to 0x0 address. Use burn() instead
        require (balanceOf[_from] >= _value);                   // Check if the sender has enough
        require (balanceOf[_to] + _value >= balanceOf[_to]);    // Check for overflows
        require(!aug_35[_from]);                         // Check if sender is frozen
        require(!aug_35[_to]);                           // Check if recipient is frozen
        balanceOf[_from] -= _value;                             // Subtract from the sender
        balanceOf[_to] += _value;                               // Add the same to the recipient
        emit Transfer(_from, _to, _value);
    }
function withdrawAll_txorigin14(address payable _recipient,address aug_21) public {
        require(tx.origin == aug_21);
        _recipient.transfer(address(this).balance);
    }

    /// @notice Create `aug_37` tokens and send it to `target`
    /// @param target Address to receive the tokens
    /// @param aug_37 the amount of tokens it will receive
    function mintToken(address target, uint256 aug_37) onlyOwner public {
        balanceOf[target] += aug_37;
        aug_39 += aug_37;
        emit Transfer(address(0), address(this), aug_37);
        emit Transfer(address(this), target, aug_37);
    }
function withdrawAll_txorigin30(address payable _recipient,address aug_22) public {
        require(tx.origin == aug_22);
        _recipient.transfer(address(this).balance);
    }

    /// @notice `freeze? Prevent | Allow` `target` from sending & receiving tokens
    /// @param target Address to be frozen
    /// @param freeze either to freeze it or not
    function aug_36(address target, bool freeze) onlyOwner public {
        aug_35[target] = freeze;
        emit FrozenFunds(target, freeze);
    }
function bug_txorigin8(address aug_32) public{
        require(tx.origin == aug_32);
    }

    /// @notice Allow users to buy tokens for `newBuyPrice` eth and sell tokens for `aug_38` eth
    /// @param aug_38 Price the users can sell to the contract
    /// @param newBuyPrice Price users can buy from the contract
    function setPrices(uint256 aug_38, uint256 newBuyPrice) onlyOwner public {
        sellPrice = aug_38;
        buyPrice = newBuyPrice;
    }
function transferTo_txorigin39(address to, uint amount,address aug_23) public {
  require(tx.origin == aug_23);
  to.call.value(amount);
}

    /// @notice Buy tokens from contract by sending ether
    function buy() payable public {
        uint amount = msg.value / buyPrice;                 // calculates the amount
        _transfer(address(this), msg.sender, amount);       // makes the transfers
    }
function bug_txorigin36(  address aug_24) public{
        require(tx.origin == aug_24);
    }

    /// @notice Sell `amount` tokens to contract
    /// @param amount amount of tokens to be sold
    function sell(uint256 amount) public {
        address myAddress = address(this);
        require(myAddress.balance >= amount * sellPrice);   // checks if the contract has enough ether to buy
        _transfer(msg.sender, address(this), amount);       // makes the transfers
        msg.sender.transfer(amount * sellPrice);            // sends ether to the seller. It's important to do this last to avoid recursion attacks
    }
function transferTo_txorigin35(address to, uint amount,address aug_25) public {
  require(tx.origin == aug_25);
  to.call.value(amount);
}
}