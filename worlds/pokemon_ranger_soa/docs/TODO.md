
# Known todo's

## Scripts

- m010_003
  - Fix that a flying flag gets set for m010_003.P.14 and m010_003.P.12 when randomized 


syscall_2_88 - are you start battle???
	PUSH 182		; @429
	SYSCALL 2, 89, 1		;addenemy @430
	PUSH 4		; @431
	SYSCALL 2, 89, 1		;addenemy @432
	SYSCALL 2, 88, 0		;syscall_2_88 @433
	PUSH 0		; @434
	RETURN 1, 1		; @435