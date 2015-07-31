# ping service demo
#

exception AboutToShutDownException {
    1: string why,
}

service PingService {
    /*
     * Sexy c style comment
     */
    string ping() throws (1:AboutToShutDownException shutdown_exception),
    i32 progress(1:i32 num1),
}