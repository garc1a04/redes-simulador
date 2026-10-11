def calculate_checksum(data):
    """
    Calculates the 16-bit 1's complement of the 1's complement sum of the given data.
    This function implements the standard Internet Checksum algorithm (RFC 1071),
    which is required to validate UDP datagrams.
    
    :param data: The payload to be checksummed. Can be a string or bytes.
    :return: An integer representing the 16-bit checksum.
    """
    # Ensure data is in bytes format for bitwise operations
    if isinstance(data, str):
        data = data.encode('utf-8')

    # If the data length is odd, pad with a zero byte at the end
    if len(data) % 2 != 0:
        data += b'\x00'

    checksum = 0

    # Iterate over the data in 16-bit (2 bytes) chunks
    for i in range(0, len(data), 2):
        # Combine two 8-bit bytes into one 16-bit word
        word = (data[i] << 8) + data[i + 1]
        checksum += word

        # Add the carry (if any) back to the 16-bit value
        checksum = (checksum & 0xFFFF) + (checksum >> 16)

    # Perform the 1's complement (invert all bits) and mask to 16 bits
    final_checksum = ~checksum & 0xFFFF

    return final_checksum


def is_checksum_valid(data, received_checksum):
    """
    Validates the integrity of the data by comparing the calculated checksum
    with the received checksum.
    
    :param data: The payload received.
    :param received_checksum: The checksum value that arrived with the datagram.
    :return: True if the calculated checksum matches the received one, False otherwise.
    """
    calculated = calculate_checksum(data)
    return calculated == received_checksum