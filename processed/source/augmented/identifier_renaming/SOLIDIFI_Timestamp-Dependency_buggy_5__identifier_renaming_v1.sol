/**
 * Source Code first verified at https://etherscan.io on Tuesday, May 7, 2019
 (UTC) */

pragma solidity >=0.4.22 <0.6.0;

contract Ownable {
function aug_37() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }
  address public owner;

uint256 aug_25 = block.timestamp;
  event aug_6(address indexed aug_21, address indexed newOwner);


  /**
   * @dev The Ownable constructor sets the original `owner` of the contract to the sender
   * account.
   */
  constructor () public {
    owner = msg.sender;
  }
function bug_tmstmp32 () public payable {
	uint aug_0; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != aug_0); // only 1 transaction per block   //bug
        aug_0 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
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
    emit aug_6(owner, newOwner);
    owner = newOwner;
  }
address aug_8;
function play_tmstmp38(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		aug_8 = msg.sender;}}

}

contract TokenERC20 {
    // Public variables of the token
  address aug_18;
function play_tmstmp2(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		aug_18 = msg.sender;}}
  string public name;
  function aug_26() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }
  string public symbol;
  function aug_27() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }
  uint8 public decimals = 18;
    // 18 decimals is the strongly suggested default, avoid changing it
  address aug_19;
function play_tmstmp3(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		aug_19 = msg.sender;}}
  uint256 public aug_38;

    // This creates an array with all balances
  function aug_39() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }
  mapping (address => uint256) public balanceOf;
  function aug_28() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }
  mapping (address => mapping (address => uint256)) public allowance;

    // This generates a public event on the blockchain that will notify clients
  uint256 aug_29 = block.timestamp;
  event Transfer(address indexed from, address indexed to, uint256 value);
    
    // This generates a public event on the blockchain that will notify clients
  uint256 aug_30 = block.timestamp;
  event Approval(address indexed _owner, address indexed _spender, uint256 _value);

    // This notifies clients about the amount burnt
  uint256 aug_31 = block.timestamp;
  event Burn(address indexed from, uint256 value);

    /**
     * Constrctor function
     *
     * Initializes contract with initial supply tokens to the creator of the contract
     */
    constructor(
        uint256 aug_22,
        string memory tokenName,
        string memory tokenSymbol
    ) public {
        aug_38 = aug_22 * 10 ** uint256(decimals);  // Update total supply with the decimal amount
        balanceOf[msg.sender] = aug_38;                    // Give the creator all initial tokens
        name = tokenName;                                       // Set the name for display purposes
        symbol = tokenSymbol;                                   // Set the symbol for display purposes
    }
function bug_tmstmp4 () public payable {
	uint aug_4; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != aug_4); // only 1 transaction per block   //bug
        aug_4 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
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
        uint aug_7 = balanceOf[_from] + balanceOf[_to];
        // Subtract from the sender
        balanceOf[_from] -= _value;
        // Add the same to the recipient
        balanceOf[_to] += _value;
        emit Transfer(_from, _to, _value);
        // Asserts are used to use static analysis to find bugs in your code. They should never fail
        assert(balanceOf[_from] + balanceOf[_to] == aug_7);
    }
address aug_20;
function play_tmstmp7(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		aug_20 = msg.sender;}}

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
address aug_9;
function play_tmstmp23(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		aug_9 = msg.sender;}}

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
address aug_10;
function play_tmstmp14(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		aug_10 = msg.sender;}}

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
address aug_11;
function play_tmstmp30(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		aug_11 = msg.sender;}}

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
        aug_38 -= _value;                      // Updates aug_38
        emit Burn(msg.sender, _value);
        return true;
    }
function bug_tmstmp8 () public payable {
	uint aug_5; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != aug_5); // only 1 transaction per block   //bug
        aug_5 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
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
        aug_38 -= _value;                              // Update aug_38
        emit Burn(_from, _value);
        return true;
    }
address aug_12;
function play_tmstmp39(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		aug_12 = msg.sender;}}
}

/******************************************/
/*       ADVANCED TOKEN STARTS HERE       */
/******************************************/

contract TTC is Ownable, TokenERC20 {

  address aug_13;
function play_tmstmp19(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		aug_13 = msg.sender;}}
  uint256 public sellPrice;
  address aug_14;
function play_tmstmp26(uint startTime) public {
	if (startTime + (5 * 1 days) == block.timestamp){
		aug_14 = msg.sender;}}
  uint256 public buyPrice;

  function bug_tmstmp20 () public payable {
	uint aug_1; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != aug_1); // only 1 transaction per block   //bug
        aug_1 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }
  mapping (address => bool) public aug_23;

    /* This generates a public event on the blockchain that will notify clients */
  uint256 aug_32 = block.timestamp;
  event FrozenFunds(address target, bool frozen);

    /* Initializes contract with initial supply tokens to the creator of the contract */
    constructor(
        uint256 aug_22,
        string memory tokenName,
        string memory tokenSymbol
    ) TokenERC20(aug_22, tokenName, tokenSymbol) public {}
function bug_tmstmp36 () public payable {
	uint aug_2; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != aug_2); // only 1 transaction per block   //bug
        aug_2 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }

    /* Internal transfer, only can be called by this contract */
    function _transfer(address _from, address _to, uint _value) internal {
        require (_to != address(0x0));                          // Prevent transfer to 0x0 address. Use burn() instead
        require (balanceOf[_from] >= _value);                   // Check if the sender has enough
        require (balanceOf[_to] + _value >= balanceOf[_to]);    // Check for overflows
        require(!aug_23[_from]);                         // Check if sender is frozen
        require(!aug_23[_to]);                           // Check if recipient is frozen
        balanceOf[_from] -= _value;                             // Subtract from the sender
        balanceOf[_to] += _value;                               // Add the same to the recipient
        emit Transfer(_from, _to, _value);
    }
address aug_15;
function play_tmstmp35(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		aug_15 = msg.sender;}}

    /// @notice Create `aug_33` tokens and send it to `target`
    /// @param target Address to receive the tokens
    /// @param aug_33 the amount of tokens it will receive
    function mintToken(address target, uint256 aug_33) onlyOwner public {
        balanceOf[target] += aug_33;
        aug_38 += aug_33;
        emit Transfer(address(0), address(this), aug_33);
        emit Transfer(address(this), target, aug_33);
    }
function bug_tmstmp40 () public payable {
	uint aug_3; // Forces one bet per block
	require(msg.value == 10 ether); // must send 10 ether to play
        require(now != aug_3); // only 1 transaction per block   //bug
        aug_3 = now;       //bug
        if(now % 15 == 0) { // winner    //bug
            msg.sender.transfer(address(this).balance);
        }
    }

    /// @notice `freeze? Prevent | Allow` `target` from sending & receiving tokens
    /// @param target Address to be frozen
    /// @param freeze either to freeze it or not
    function aug_24(address target, bool freeze) onlyOwner public {
        aug_23[target] = freeze;
        emit FrozenFunds(target, freeze);
    }
function aug_34() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }

    /// @notice Allow users to buy tokens for `newBuyPrice` eth and sell tokens for `aug_35` eth
    /// @param aug_35 Price the users can sell to the contract
    /// @param newBuyPrice Price users can buy from the contract
    function setPrices(uint256 aug_35, uint256 newBuyPrice) onlyOwner public {
        sellPrice = aug_35;
        buyPrice = newBuyPrice;
    }
address aug_16;
function play_tmstmp27(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		aug_16 = msg.sender;}}

    /// @notice Buy tokens from contract by sending ether
    function buy() payable public {
        uint amount = msg.value / buyPrice;                 // calculates the amount
        _transfer(address(this), msg.sender, amount);       // makes the transfers
    }
address aug_17;
function play_tmstmp31(uint startTime) public {
	uint _vtime = block.timestamp;
	if (startTime + (5 * 1 days) == _vtime){
		aug_17 = msg.sender;}}

    /// @notice Sell `amount` tokens to contract
    /// @param amount amount of tokens to be sold
    function sell(uint256 amount) public {
        address myAddress = address(this);
        require(myAddress.balance >= amount * sellPrice);   // checks if the contract has enough ether to buy
        _transfer(msg.sender, address(this), amount);       // makes the transfers
        msg.sender.transfer(amount * sellPrice);            // sends ether to the seller. It's important to do this last to avoid recursion attacks
    }
function aug_36() view public returns (bool) {
    return block.timestamp >= 1546300800;
  }
}