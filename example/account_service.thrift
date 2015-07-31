struct UserInfo {
    1: required i32 id,
    2: required string username,
}

service AccountService {
    UserInfo get_user_by_id(1:i32 id),
}